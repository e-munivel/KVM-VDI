package provider

import (
	"context"
	"errors"
	"fmt"
	"regexp"

	"gitlab.com/isard/isardvdi/authentication/model"
	"gitlab.com/isard/isardvdi/authentication/provider/types"
	"gitlab.com/isard/isardvdi/authentication/token"

	r "gopkg.in/rethinkdb/rethinkdb-go.v6"
)

const (
	TokenArgsKey                        = "token"
	ProviderArgsKey                     = "provider"
	CategoryIDArgsKey                   = "category_id"
	RequestBodyArgsKey                  = "request_body"
	RedirectArgsKey                     = "redirect"
	FormUsernameArgsKey                 = "form_username"
	FormPasswordArgsKey                 = "form_password"
	HTTPRequest         HTTPRequestType = "req"
)

type HTTPRequestType string

type LoginArgs struct {
	Token    *string
	Redirect *string

	FormUsername *string
	FormPassword *string
}

type CallbackArgs struct {
	Oauth2Code *string
}

type Provider interface {
	Login(ctx context.Context, categoryID string, args LoginArgs) (g *model.Group, u *types.ProviderUserData, redirect string, tkn string, err *ProviderError)
	Callback(ctx context.Context, claims *token.CallbackClaims, args CallbackArgs) (g *model.Group, u *types.ProviderUserData, redirect string, tkn string, err *ProviderError)
	AutoRegister() bool
	String() string
	Healthcheck() error
}

type ProviderError struct {
	// The error that will be shown to the user
	User error
	// Detail of the error that will be logged in debug
	Detail error
}

func (p *ProviderError) Error() string {
	return fmt.Errorf("%w: %w", p.User, p.Detail).Error()
}

func (p *ProviderError) Is(target error) bool {
	return errors.Is(p.User, target)
}

func (p *ProviderError) Unwrap() error {
	return p.Detail
}

var (
	ErrInternal           = errors.New("internal server error")
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrUserDisabled       = errors.New("disabled user")
	ErrUnknownIDP         = errors.New("unknown identity provider")
	errInvalidIDP         = errors.New("invalid identity provider for this operation")
)

type Unknown struct{}

func (Unknown) String() string {
	return types.ProviderUnknown
}

func (Unknown) Login(context.Context, string, LoginArgs) (*model.Group, *types.ProviderUserData, string, string, *ProviderError) {
	return nil, nil, "", "", &ProviderError{
		User:   ErrUnknownIDP,
		Detail: errors.New("unknown provider"),
	}
}

func (Unknown) Callback(context.Context, *token.CallbackClaims, CallbackArgs) (*model.Group, *types.ProviderUserData, string, string, *ProviderError) {
	return nil, nil, "", "", &ProviderError{
		User:   ErrUnknownIDP,
		Detail: errors.New("unknown provider"),
	}
}

func (Unknown) AutoRegister() bool {
	return false
}

func (Unknown) Healthcheck() error {
	return nil
}

func matchRegex(re *regexp.Regexp, s string) string {
	result := re.FindStringSubmatch(s)
	// the first submatch is the whole match, the 2nd is the 1st group
	if len(result) > 1 {
		return result[1]
	}

	return re.FindString(s)
}

func matchRegexMultiple(re *regexp.Regexp, s string) []string {
	allMatches := []string{}

	// Attempt to match all the groups
	result := re.FindAllStringSubmatch(s, -1)
	if len(result) == 1 {
		// If no groups are found, attempt to do a global match
		global := re.FindString(s)
		if global == "" {
			return allMatches
		}

		return []string{global}
	}

	for _, r := range result {
		// Extract the matched group
		if len(r) > 1 {
			allMatches = append(allMatches, r[1])
		}
	}

	return allMatches
}

func guessCategory(ctx context.Context, db r.QueryExecutor, secret string, re *regexp.Regexp, rawCategories []string, u *types.ProviderUserData) (string, *ProviderError) {
	categories := []*model.Category{}
	for _, c := range rawCategories {
		match := matchRegexMultiple(re, c)
		for _, m := range match {
			category := &model.Category{
				ID: m,
			}

			exists, err := category.Exists(ctx, db)
			if err != nil {
				return "", &ProviderError{
					User:   ErrInternal,
					Detail: fmt.Errorf("check category exists: %w", err),
				}
			}

			if !exists {
				continue
			}

			// TODO: Maybe we need to add a UID field in the category table to represent the external ID of this group and make the mapping like so????
			categories = append(categories, category)
		}
	}

	switch len(categories) {
	case 0:
		return "", &ProviderError{
			User:   ErrInvalidCredentials,
			Detail: fmt.Errorf("user doesn't have any valid category, recieved raw argument: '%s'", rawCategories),
		}

	case 1:
		u.Category = categories[0].ID
		return "", nil

	default:
		tkn, err := token.SignCategorySelectToken(secret, categories, u)
		if err != nil {
			return "", &ProviderError{
				User:   ErrInternal,
				Detail: fmt.Errorf("sign category select token: %w", err),
			}
		}

		return tkn, nil
	}
}
