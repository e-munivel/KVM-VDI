package token

import (
	"fmt"
	"time"

	"gitlab.com/isard/isardvdi/authentication/authentication/provider/types"
	"gitlab.com/isard/isardvdi/authentication/model"

	"github.com/golang-jwt/jwt/v5"
)

const (
	issuer = "isard-authentication"
	// TODO: Other signing keys
	keyID = "isardvdi"
)

// TODO: Maybe this should be configuable
var signingMethod = jwt.SigningMethodHS256

func SignLoginToken(secret string, duration time.Duration, u *model.User) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &LoginClaims{
		RegisteredClaims: &jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(duration)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			NotBefore: jwt.NewNumericDate(time.Now()),
			Issuer:    issuer,
		},
		KeyID: keyID,
		Data: LoginClaimsData{
			Provider:   u.Provider,
			ID:         u.ID,
			RoleID:     string(u.Role),
			CategoryID: u.Category,
			GroupID:    u.Group,
			Name:       u.Name,
		},
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the token: %w", err)
	}

	return ss, nil
}

func SignRegisterToken(secret string, duration time.Duration, u *model.User) (string, error) {
	// If the provider is local or ldap, use the user facing provider 'form'
	p := u.Provider
	if u.Provider == types.Local || u.Provider == types.LDAP {
		p = types.Form
	}

	tkn := jwt.NewWithClaims(signingMethod, &RegisterClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(duration)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypeRegister,
		},
		Provider:   p,
		UserID:     u.UID,
		Username:   u.Username,
		CategoryID: u.Category,
		Name:       u.Name,
		Email:      u.Email,
		Photo:      u.Photo,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the register token: %w", err)
	}

	return ss, nil
}

func SignCallbackToken(secret, prv, cat, redirect string) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &CallbackClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				// TODO: This should be maybe configurable
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(10 * time.Minute)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypeCallback,
		},
		Provider:   prv,
		CategoryID: cat,
		Redirect:   redirect,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the callback token: %w", err)
	}

	return ss, nil
}

func SignDisclaimerAcknowledgementRequiredToken(secret string, userID string) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &DisclaimerAcknowledgementRequiredClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				// TODO: This should be maybe configurable
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(10 * time.Minute)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypeDisclaimerAcknowledgementRequired,
		},
		UserID: userID,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the disclaimer acknowledgement required token: %w", err)
	}

	return ss, nil
}

func SignEmailVerificationRequiredToken(secret string, u *model.User) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &EmailVerificationRequiredClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				// TODO: This should be maybe configurable
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(10 * time.Minute)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypeEmailVerificationRequired,
		},
		UserID:       u.ID,
		CategoryID:   u.Category,
		CurrentEmail: u.Email,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the email verification required token: %w", err)
	}

	return ss, nil
}

func SignEmailVerificationToken(secret string, userID string, email string) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &EmailVerificationClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				// TODO: This should be maybe configurable
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(60 * time.Minute)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypeEmailVerification,
		},
		UserID: userID,
		Email:  email,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the email verification token: %w", err)
	}

	return ss, nil
}

func SignPasswordResetRequiredToken(secret string, userID string) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &PasswordResetRequiredClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				// TODO: This should be maybe configurable
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(60 * time.Minute)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypePasswordResetRequired,
		},
		UserID: userID,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the password reset required token: %w", err)
	}

	return ss, nil
}

func SignPasswordResetToken(secret string, userID string) (string, error) {
	tkn := jwt.NewWithClaims(signingMethod, &PasswordResetClaims{
		TypeClaims: TypeClaims{
			RegisteredClaims: &jwt.RegisteredClaims{
				// TODO: This should be maybe configurable
				ExpiresAt: jwt.NewNumericDate(time.Now().Add(60 * time.Minute)),
				IssuedAt:  jwt.NewNumericDate(time.Now()),
				NotBefore: jwt.NewNumericDate(time.Now()),
				Issuer:    issuer,
			},
			KeyID: keyID,
			Type:  TypePasswordReset,
		},
		UserID: userID,
	})

	ss, err := tkn.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("sign the password reset token: %w", err)
	}

	return ss, nil
}
