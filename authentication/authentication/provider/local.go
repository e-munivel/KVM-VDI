package provider

import (
	"context"
	"errors"
	"fmt"

	"gitlab.com/isard/isardvdi/authentication/authentication/provider/types"
	"gitlab.com/isard/isardvdi/authentication/authentication/token"
	"gitlab.com/isard/isardvdi/authentication/model"
	"gitlab.com/isard/isardvdi/pkg/db"

	"golang.org/x/crypto/bcrypt"
	r "gopkg.in/rethinkdb/rethinkdb-go.v6"
)

type Local struct {
	db r.QueryExecutor
}

func InitLocal(db r.QueryExecutor) *Local {
	return &Local{db}
}

func (l *Local) Login(ctx context.Context, categoryID string, args map[string]string) (*model.Group, *model.User, string, error) {
	usr := args[FormUsernameArgsKey]
	pwd := args[FormPasswordArgsKey]

	u := &model.User{
		UID:      usr,
		Username: usr,
		Provider: types.Local,
		Category: categoryID,
	}
	if err := u.LoadWithoutID(ctx, l.db); err != nil {
		if errors.Is(err, db.ErrNotFound) {
			return nil, nil, "", ErrInvalidCredentials
		}

		return nil, nil, "", fmt.Errorf("load user from DB: %w", err)
	}

	if err := bcrypt.CompareHashAndPassword([]byte(u.Password), []byte(pwd)); err != nil {
		return nil, nil, "", ErrInvalidCredentials
	}

	return nil, u, "", nil
}

func (l *Local) Callback(context.Context, *token.CallbackClaims, map[string]string) (*model.Group, *model.User, string, error) {
	return nil, nil, "", errInvalidIDP
}

func (Local) AutoRegister() bool {
	return false
}

func (l *Local) String() string {
	return types.Local
}
