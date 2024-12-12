package authentication

import (
	"context"
	"errors"
	"fmt"
	"time"

	"gitlab.com/isard/isardvdi/authentication/model"
	"gitlab.com/isard/isardvdi/authentication/provider"
	"gitlab.com/isard/isardvdi/authentication/provider/types"
	"gitlab.com/isard/isardvdi/authentication/token"
	"gitlab.com/isard/isardvdi/pkg/db"
	sessionsv1 "gitlab.com/isard/isardvdi/pkg/gen/proto/go/sessions/v1"
)

func (a *Authentication) Login(ctx context.Context, prv, categoryID string, args provider.LoginArgs, remoteAddr string) (string, string, error) {
	if args.Redirect == nil {
		redirect := ""
		args.Redirect = &redirect
	}

	// Check if the user sends a token
	if args.Token != nil {
		typ, err := token.GetTokenType(*args.Token)
		if err != nil {
			return "", "", fmt.Errorf("get the JWT token type: %w", err)
		}

		switch typ {
		case token.TypeRegister:
			return a.finishRegister(ctx, remoteAddr, *args.Token, *args.Redirect)

		case token.TypeDisclaimerAcknowledgementRequired:
			return a.finishDisclaimerAcknowledgement(ctx, remoteAddr, *args.Token, *args.Redirect)

		case token.TypePasswordResetRequired:
			return a.finishPasswordReset(ctx, remoteAddr, *args.Token, *args.Redirect)

		case token.TypeCategorySelect:
			return a.finishCategorySelect(ctx, remoteAddr, categoryID, *args.Token, *args.Redirect)
		}
	}

	// Get the provider
	p := a.Provider(prv)

	// Log in
	g, secondary, u, redirect, ss, lErr := p.Login(ctx, categoryID, args)
	if lErr != nil {
		a.Log.Info().Str("prv", p.String()).Err(lErr).Msg("login failed")

		return "", "", fmt.Errorf("login: %w", lErr)
	}

	// If the provider forces us to redirect, do it
	if redirect != "" {
		return "", redirect, nil
	}

	// If the provider returns a token return it
	if ss != "" {
		return ss, redirect, nil
	}

	// Continue with the login process, passing the redirect path that has been
	// requested by the user
	return a.startLogin(ctx, remoteAddr, p, g, secondary, u, *args.Redirect)
}

func (a *Authentication) Callback(ctx context.Context, ss string, args provider.CallbackArgs, remoteAddr string) (string, string, error) {
	claims, err := token.ParseCallbackToken(a.Secret, ss)
	if err != nil {
		return "", "", fmt.Errorf("parse callback state: %w", err)
	}

	// Get the provider
	p := a.Provider(claims.Provider)

	// Callback
	g, secondary, u, redirect, ss, cErr := p.Callback(ctx, claims, args)
	if cErr != nil {
		a.Log.Info().Str("prv", p.String()).Err(cErr).Msg("callback failed")

		return "", "", fmt.Errorf("callback: %w", cErr)
	}

	if redirect == "" {
		redirect = claims.Redirect
	}

	// If the provider returns a token return it
	if ss != "" {
		return ss, redirect, nil
	}

	return a.startLogin(ctx, remoteAddr, p, g, secondary, u, redirect)
}

func (a *Authentication) startLogin(ctx context.Context, remoteAddr string, p provider.Provider, g *model.Group, secondary []*model.Group, data *types.ProviderUserData, redirect string) (string, string, error) {
	u := data.ToUser()

	uExists, err := u.Exists(ctx, a.DB)
	if err != nil {
		return "", "", fmt.Errorf("check if user exists: %w", err)
	}

	// Remove weird characters from the user and group names
	normalizeIdentity(g, u)

	if !uExists {
		// Manual registration
		if !p.AutoRegister(u) {
			// If the user has logged in correctly, but doesn't exist in the DB, they have to register first!
			ss, err := token.SignRegisterToken(a.Secret, u)

			a.Log.Info().Err(err).Str("usr", u.UID).Str("tkn", ss).Msg("register token signed")

			return ss, redirect, err
		}

		// Automatic group registration!
		for _, group := range append(secondary, g) {
			gExists, err := group.Exists(ctx, a.DB)
			if err != nil {
				return "", "", fmt.Errorf("check if group exists: %w", err)
			}

			if !gExists {
				if err := a.registerGroup(group); err != nil {
					return "", "", fmt.Errorf("auto register group: %w", err)
				}
			}
		}

		// Set the user group to the new group created
		u.Group = g.ID
		for _, group := range secondary {
			u.SecondaryGroups = append(u.SecondaryGroups, group.ID)
		}

		// Automatic registration!
		if err := a.registerUser(u); err != nil {
			return "", "", fmt.Errorf("auto register user: %w", err)
		}
	}

	return a.finishLogin(ctx, remoteAddr, u, redirect)
}

func (a *Authentication) finishLogin(ctx context.Context, remoteAddr string, u *model.User, redirect string) (string, string, error) {
	// Check if the user is disabled
	if !u.Active {
		return "", "", provider.ErrUserDisabled
	}

	// Check if the user needs to acknowledge the disclaimer
	dscl, err := a.API.AdminUserRequiredDisclaimerAcknowledgement(ctx, u.ID)
	if err != nil {
		return "", "", fmt.Errorf("check if the user needs to accept the disclaimer: %w", err)
	}
	if dscl {
		ss, err := token.SignDisclaimerAcknowledgementRequiredToken(a.Secret, u.ID)
		if err != nil {
			return "", "", err
		}

		return ss, redirect, nil
	}

	// TODO: Check if the user needs to migrate themselves
	if false {
		ss, err := token.SignUserMigrationRequiredToken(a.Secret, u.ID)
		if err != nil {
			return "", "", err
		}

		return ss, redirect, nil
	}

	// Check if the user has the email verified
	vfEmail, err := a.API.AdminUserRequiredEmailVerification(ctx, u.ID)
	if err != nil {
		return "", "", fmt.Errorf("check if the user needs to verify the email: %w", err)
	}
	if vfEmail {
		ss, err := token.SignEmailVerificationRequiredToken(a.Secret, u)
		if err != nil {
			return "", "", err
		}

		return ss, redirect, nil
	}

	pwdRst, err := a.API.AdminUserRequiredPasswordReset(ctx, u.ID)
	if err != nil {
		return "", "", fmt.Errorf("check if the user needs to reset the password: %w", err)
	}
	if pwdRst {
		ss, err := token.SignPasswordResetRequiredToken(a.Secret, u.ID)
		if err != nil {
			return "", "", err
		}

		return ss, redirect, nil
	}

	// Set the last accessed time of the user
	u.Accessed = float64(time.Now().Unix())

	// Load the rest of the data of the user from the DB without overriding the data provided by the
	// login provider
	u2 := &model.User{ID: u.ID}
	if err := u2.Load(ctx, a.DB); err != nil {
		return "", "", fmt.Errorf("load user from DB: %w", err)
	}

	u.LoadWithoutOverride(u2)
	normalizeIdentity(nil, u)

	// Update the user in the DB with the latest data
	if err := u.Update(ctx, a.DB); err != nil {
		return "", "", fmt.Errorf("update user in the DB: %w", err)
	}

	// Create the session
	sess, err := a.Sessions.New(ctx, &sessionsv1.NewRequest{
		UserId:     u.ID,
		RemoteAddr: remoteAddr,
	})
	if err != nil {
		return "", "", fmt.Errorf("create the session: %w", err)
	}

	ss, err := token.SignLoginToken(a.Secret, sess.Time.ExpirationTime.AsTime(), sess.GetId(), u)
	if err != nil {
		return "", "", err
	}

	a.Log.Info().Str("usr", u.ID).Str("tkn", ss).Str("redirect", redirect).Msg("login succeeded")

	return ss, redirect, nil
}

func (a *Authentication) finishRegister(ctx context.Context, remoteAddr, ss, redirect string) (string, string, error) {
	claims, err := token.ParseRegisterToken(a.Secret, ss)
	if err != nil {
		return "", "", err
	}

	u := &model.User{
		Provider: claims.Provider,
		Category: claims.CategoryID,
		UID:      claims.UserID,
	}
	if err := u.LoadWithoutID(ctx, a.DB); err != nil {
		if errors.Is(err, db.ErrNotFound) {
			return "", "", errors.New("user not registered")
		}

		return "", "", fmt.Errorf("load user from db: %w", err)
	}

	ss, redirect, err = a.finishLogin(ctx, remoteAddr, u, redirect)
	if err != nil {
		return "", "", err
	}

	a.Log.Info().Str("usr", u.ID).Str("tkn", ss).Msg("register succeeded")

	return ss, redirect, nil
}

func (a *Authentication) finishDisclaimerAcknowledgement(ctx context.Context, remoteAddr, ss, redirect string) (string, string, error) {
	claims, err := token.ParseDisclaimerAcknowledgementRequiredToken(a.Secret, ss)
	if err != nil {
		return "", "", err
	}

	u := &model.User{ID: claims.UserID}
	if err := u.Load(ctx, a.DB); err != nil {
		return "", "", fmt.Errorf("load user from db: %w", err)
	}

	return a.finishLogin(ctx, remoteAddr, u, redirect)
}

func (a *Authentication) finishPasswordReset(ctx context.Context, remoteAddr, ss, redirect string) (string, string, error) {
	claims, err := token.ParsePasswordResetRequiredToken(a.Secret, ss)
	if err != nil {
		return "", "", err
	}

	u := &model.User{ID: claims.UserID}
	if err := u.Load(ctx, a.DB); err != nil {
		return "", "", fmt.Errorf("load user from db: %w", err)
	}

	return a.finishLogin(ctx, remoteAddr, u, redirect)
}

func (a *Authentication) finishCategorySelect(ctx context.Context, remoteAddr, categoryID, ss, redirect string) (string, string, error) {
	claims, err := token.ParseCategorySelectToken(a.Secret, ss)
	if err != nil {
		return "", "", err
	}

	u := &claims.User
	u.Category = categoryID

	return a.startLogin(ctx, remoteAddr, a.Provider(claims.User.Provider), nil, []*model.Group{}, u, redirect)
}
