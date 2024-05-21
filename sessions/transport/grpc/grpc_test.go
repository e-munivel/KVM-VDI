package grpc_test

import (
	"context"
	"errors"
	"fmt"
	"os"
	"testing"
	"time"

	sessionsv1 "gitlab.com/isard/isardvdi/pkg/gen/proto/go/sessions/v1"
	"gitlab.com/isard/isardvdi/pkg/redis"
	"gitlab.com/isard/isardvdi/sessions/model"
	"gitlab.com/isard/isardvdi/sessions/sessions"
	"gitlab.com/isard/isardvdi/sessions/transport/grpc"

	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func TestNew(t *testing.T) {
	assert := assert.New(t)

	now := time.Now()

	cases := map[string]struct {
		PrepareSessions func(*sessions.SessionsMock)
		Req             *sessionsv1.NewRequest
		ExpectedRsp     *sessionsv1.NewResponse
		ExpectedErr     string
	}{
		"should work as expected": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("New", mock.AnythingOfType("context.backgroundCtx"), "nefix").
					Return(&model.Session{
						ID: "hola Néfix :)",
						Time: &model.SessionTime{
							MaxTime:        now,
							MaxRenewTime:   now,
							ExpirationTime: now,
						},
					}, nil)
			},
			Req: &sessionsv1.NewRequest{
				UserId: "nefix",
			},
			ExpectedRsp: &sessionsv1.NewResponse{
				Id: "hola Néfix :)",
				Time: &sessionsv1.NewResponseTime{
					MaxTime:        timestamppb.New(now),
					MaxRenewTime:   timestamppb.New(now),
					ExpirationTime: timestamppb.New(now),
				},
			},
		},
		"should return an Internal status if an unexpected error occurs": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("New", mock.AnythingOfType("context.backgroundCtx"), "nefix").
					Return(&model.Session{}, errors.New("unexpected error"))
			},
			Req: &sessionsv1.NewRequest{
				UserId: "nefix",
			},
			ExpectedErr: status.Error(codes.Internal, fmt.Errorf("create new session: %w", errors.New("unexpected error")).Error()).Error(),
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)

			sessionsMock := sessions.NewSessionsMock()
			tc.PrepareSessions(sessionsMock)

			srv := grpc.NewSessionsServer(&log, nil, "", sessionsMock)

			rsp, err := srv.New(context.Background(), tc.Req)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			assert.Equal(tc.ExpectedRsp, rsp)

			sessionsMock.AssertExpectations(t)
		})
	}
}

func TestGet(t *testing.T) {
	assert := assert.New(t)

	now := time.Now()

	cases := map[string]struct {
		PrepareSessions func(*sessions.SessionsMock)
		Req             *sessionsv1.GetRequest
		ExpectedRsp     *sessionsv1.GetResponse
		ExpectedErr     string
	}{
		"should work as expected": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Get", mock.AnythingOfType("context.backgroundCtx"), "hola Melina :)").
					Return(&model.Session{
						ID: "hola Melina :)",
						Time: &model.SessionTime{
							MaxTime:        now,
							MaxRenewTime:   now,
							ExpirationTime: now,
						},
					}, nil)
			},
			Req: &sessionsv1.GetRequest{
				Id: "hola Melina :)",
			},
			ExpectedRsp: &sessionsv1.GetResponse{
				Time: &sessionsv1.GetResponseTime{
					MaxTime:        timestamppb.New(now),
					MaxRenewTime:   timestamppb.New(now),
					ExpirationTime: timestamppb.New(now),
				},
			},
		},
		"should return an NotFound status if the session is not found": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Get", mock.AnythingOfType("context.backgroundCtx"), "hola Pau :)").
					Return(&model.Session{}, redis.ErrNotFound)
			},
			Req: &sessionsv1.GetRequest{
				Id: "hola Pau :)",
			},
			ExpectedErr: status.Error(codes.NotFound, redis.ErrNotFound.Error()).Error(),
		},
		"should return an Unauthenticated status if the session has expired": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Get", mock.AnythingOfType("context.backgroundCtx"), "123456789").
					Return(&model.Session{}, sessions.ErrSessionExpired)
			},
			Req: &sessionsv1.GetRequest{
				Id: "123456789",
			},
			ExpectedErr: status.Error(codes.Unauthenticated, sessions.ErrSessionExpired.Error()).Error(),
		},
		"should return an Internal status if an unexpected error occurs": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Get", mock.AnythingOfType("context.backgroundCtx"), "987654321").
					Return(&model.Session{}, errors.New("unexpected error"))
			},
			Req: &sessionsv1.GetRequest{
				Id: "987654321",
			},
			ExpectedErr: status.Error(codes.Internal, fmt.Errorf("get session: %w", errors.New("unexpected error")).Error()).Error(),
		},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)

			sessionsMock := sessions.NewSessionsMock()

			tc.PrepareSessions(sessionsMock)

			srv := grpc.NewSessionsServer(&log, nil, "", sessionsMock)

			rsp, err := srv.Get(context.Background(), tc.Req)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			assert.Equal(tc.ExpectedRsp, rsp)

			sessionsMock.AssertExpectations(t)
		})
	}
}

func TestRenew(t *testing.T) {
	assert := assert.New(t)

	now := time.Now()

	cases := map[string]struct {
		PrepareSessions func(*sessions.SessionsMock)
		Req             *sessionsv1.RenewRequest
		ExpectedRsp     *sessionsv1.RenewResponse
		ExpectedErr     string
	}{
		"should work as expected": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Renew", mock.AnythingOfType("context.backgroundCtx"), "12345").
					Return(&model.SessionTime{
						MaxTime:        now,
						MaxRenewTime:   now,
						ExpirationTime: now,
					}, nil)
			},
			Req: &sessionsv1.RenewRequest{
				Id: "12345",
			},
			ExpectedRsp: &sessionsv1.RenewResponse{
				Time: &sessionsv1.RenewResponseTime{
					MaxTime:        timestamppb.New(now),
					MaxRenewTime:   timestamppb.New(now),
					ExpirationTime: timestamppb.New(now),
				},
			},
		},
		"should return an NotFound status if the session is not found": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Renew", mock.AnythingOfType("context.backgroundCtx"), "234456").
					Return(&model.SessionTime{}, redis.ErrNotFound)
			},
			Req: &sessionsv1.RenewRequest{
				Id: "234456",
			},
			ExpectedErr: status.Error(codes.NotFound, redis.ErrNotFound.Error()).Error(),
		},
		"renew time has expired": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Renew", mock.AnythingOfType("context.backgroundCtx"), "34567").
					Return(&model.SessionTime{}, sessions.ErrRenewTimeExpired)
			},
			Req: &sessionsv1.RenewRequest{
				Id: "34567",
			},
			ExpectedErr: status.Error(codes.Unauthenticated, sessions.ErrRenewTimeExpired.Error()).Error(),
		},
		"should return an Unauthenticated error if the session has reached its max time": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Renew", mock.AnythingOfType("context.backgroundCtx"), "45678").
					Return(&model.SessionTime{}, sessions.ErrMaxSessionTime)
			},
			Req: &sessionsv1.RenewRequest{
				Id: "45678",
			},
			ExpectedErr: status.Error(codes.Unauthenticated, sessions.ErrMaxSessionTime.Error()).Error(),
		},
		"should return an Internal status if an unexpected error occurs": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Renew", mock.AnythingOfType("context.backgroundCtx"), "56789").
					Return(&model.SessionTime{}, errors.New("unexpected error"))
			},
			Req: &sessionsv1.RenewRequest{
				Id: "56789",
			},
			ExpectedErr: status.Error(codes.Internal, fmt.Errorf("renew session: %w", errors.New("unexpected error")).Error()).Error(),
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)

			sessionsMock := sessions.NewSessionsMock()
			tc.PrepareSessions(sessionsMock)

			srv := grpc.NewSessionsServer(&log, nil, "", sessionsMock)

			rsp, err := srv.Renew(context.Background(), tc.Req)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			assert.Equal(tc.ExpectedRsp, rsp)

			sessionsMock.AssertExpectations(t)
		})
	}
}

func TestRevoke(t *testing.T) {
	assert := assert.New(t)

	cases := map[string]struct {
		PrepareSessions func(*sessions.SessionsMock)
		Req             *sessionsv1.RevokeRequest
		ExpectedRsp     *sessionsv1.RevokeResponse
		ExpectedErr     string
	}{
		"should work as expected": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Revoke", mock.AnythingOfType("context.backgroundCtx"), "12345").
					Return(nil)
			},
			Req: &sessionsv1.RevokeRequest{
				Id: "12345",
			},
			ExpectedRsp: &sessionsv1.RevokeResponse{},
		},
		"should return an NotFound status if the session is not found": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Revoke", mock.AnythingOfType("context.backgroundCtx"), "aHR0cHM6Ly9odHRwLmNhdC80MDQ=").
					Return(redis.ErrNotFound)

			},
			Req: &sessionsv1.RevokeRequest{
				Id: "aHR0cHM6Ly9odHRwLmNhdC80MDQ=",
			},
			ExpectedErr: status.Error(codes.NotFound, redis.ErrNotFound.Error()).Error(),
		},
		"should return an Internal status if an unexpected error occurs": {
			PrepareSessions: func(sm *sessions.SessionsMock) {
				sm.On("Revoke", mock.AnythingOfType("context.backgroundCtx"), "aHR0cHM6Ly9odHRwLmNhdC81MDA=").
					Return(errors.New("unexpected error"))
			},
			Req: &sessionsv1.RevokeRequest{
				Id: "aHR0cHM6Ly9odHRwLmNhdC81MDA=",
			},
			ExpectedErr: status.Error(codes.Internal, fmt.Errorf("revoke session: %w", errors.New("unexpected error")).Error()).Error(),
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)

			sessionsMock := sessions.NewSessionsMock()
			tc.PrepareSessions(sessionsMock)

			srv := grpc.NewSessionsServer(&log, nil, "", sessionsMock)

			rsp, err := srv.Revoke(context.Background(), tc.Req)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			assert.Equal(tc.ExpectedRsp, rsp)

			sessionsMock.AssertExpectations(t)
		})
	}
}
