package director_test

import (
	"context"
	"os"
	"testing"
	"time"

	"gitlab.com/isard/isardvdi-cli/pkg/client"
	apiMock "gitlab.com/isard/isardvdi-cli/pkg/client/mock"
	"gitlab.com/isard/isardvdi/orchestrator/cfg"
	"gitlab.com/isard/isardvdi/orchestrator/orchestrator/director"
	operationsv1 "gitlab.com/isard/isardvdi/pkg/gen/proto/go/operations/v1"

	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestRataNeedToScaleHypervisors(t *testing.T) {
	assert := assert.New(t)

	cases := map[string]struct {
		AvailHypers               []*operationsv1.ListHypervisorsResponseHypervisor
		Hypers                    []*client.OrchestratorHypervisor
		RataMinCPU                int
		RataMinRAM                int
		RataMaxCPU                int
		RataMaxRAM                int
		ExpectedErr               string
		ExpectedRemoveDeadRow     string
		ExpectedCreateHypervisor  *operationsv1.CreateHypervisorRequest
		ExpectedAddDeadRow        string
		ExpectedDestroyHypervisor *operationsv1.DestroyHypervisorRequest
	}{
		"if there's enough RAM, it should return 0": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*client.OrchestratorHypervisor{{
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 300,
					Used:  150,
					Free:  150,
				},
			}},
			RataMinRAM: 100,
		},
		"if there's not enough RAM, it should return the ID of the hypervisor that needs to be created": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:    "testing",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   5000,
			}, {
				Id:    "HUGE HYPERVISOR",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   99999999,
			}, {
				Id:    "already",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   300,
			}},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:         "already",
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}},
			RataMinRAM: 500,
			ExpectedCreateHypervisor: &operationsv1.CreateHypervisorRequest{
				Id: "testing",
			},
		},
		"if there's too much free RAM, it should add the biggest hypervisor that it can to the dead row": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:                  "1",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 500,
					Used:  100,
					Free:  400,
				},
			}, {
				ID:                  "2",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          true,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}, {
				ID:                  "3",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 300,
					Used:  100,
					Free:  200,
				},
			}},
			RataMaxRAM:         300,
			ExpectedAddDeadRow: "2",
		},
		"if there's not enough RAM but there are hypervisors on the dead row, it should remove those from it": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:  "testing",
				Ram: 5000,
			}, {
				Id:  "HUGE HYPERVISOR",
				Ram: 99999999,
			}},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:         "existing-1",
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}, {
				ID:                  "existing-2",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          false,
				DesktopsStarted:     20,
				OrchestratorManaged: true,
				DestroyTime:         time.Now().Add(time.Hour),
				RAM: client.OrchestratorResourceLoad{
					Total: 3000,
					Used:  2000,
					Free:  1000,
				},
			}},
			RataMinRAM:            500,
			ExpectedRemoveDeadRow: "existing-2",
		},
		"if there's not enough RAM and there are multiple hypervisors on the dead row, it should remove the smallest hypervisor from it": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:  "testing",
				Ram: 5000,
			}, {
				Id:  "HUGE HYPERVISOR",
				Ram: 99999999,
			}},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:                  "existing-1",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}, {
				ID:                  "existing-2",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				DesktopsStarted:     20,
				DestroyTime:         time.Now().Add(time.Hour),
				RAM: client.OrchestratorResourceLoad{
					Total: 3000,
					Used:  2000,
					Free:  1000,
				},
			}, {
				ID:                  "existing-3",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				DesktopsStarted:     20,
				DestroyTime:         time.Now().Add(time.Hour),
				RAM: client.OrchestratorResourceLoad{
					Total: 1000,
					Used:  300,
					Free:  700,
				},
			}},
			RataMinRAM:            500,
			ExpectedRemoveDeadRow: "existing-3",
		},
		"if there's an hypervisor that's been too much time on the dead row, KILL THEM!! >:(": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:         "1",
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 500,
					Used:  400,
					Free:  100,
				},
			}, {
				ID:                  "2",
				Status:              client.HypervisorStatusOnline,
				DestroyTime:         time.Now().Add(-2 * director.DeadRowDuration),
				DesktopsStarted:     254,
				OnlyForced:          true,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}, {
				ID:         "3",
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 500,
					Used:  250,
					Free:  250,
				},
			}},
			RataMinRAM: 300,
			ExpectedDestroyHypervisor: &operationsv1.DestroyHypervisorRequest{
				Id: "2",
			},
		},
		"if there's an hypervisor that's in the dead row and has 0 desktops started, KILL THEM!! >:(": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:         "1",
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 500,
					Used:  400,
					Free:  100,
				},
			}, {
				ID:                  "2",
				Status:              client.HypervisorStatusOnline,
				DestroyTime:         time.Now().Add(2 * director.DeadRowDuration),
				DesktopsStarted:     0,
				OnlyForced:          true,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}, {
				ID:         "3",
				Status:     client.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: client.OrchestratorResourceLoad{
					Total: 500,
					Used:  250,
					Free:  250,
				},
			}},
			RataMinRAM: 300,
			ExpectedDestroyHypervisor: &operationsv1.DestroyHypervisorRequest{
				Id: "2",
			},
		},
		"if there aren't enough ram, but there's a small hyper in the dead row and with it the system can work, remove it from the dead row": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:                  "1",
				Status:              client.HypervisorStatusOnline,
				OnlyForced:          true,
				DestroyTime:         time.Now().Add(2 * director.DeadRowDuration),
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 600,
					Used:  400,
					Free:  200,
				},
			}, {
				ID:                  "2",
				Status:              client.HypervisorStatusOnline,
				DesktopsStarted:     0,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}},
			RataMinRAM:            700,
			ExpectedRemoveDeadRow: "1",
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)

			rata := director.NewRata(cfg.DirectorRata{
				MinCPU: tc.RataMinCPU,
				MinRAM: tc.RataMinRAM,
				MaxCPU: tc.RataMaxCPU,
				MaxRAM: tc.RataMaxRAM,
			}, false, &log, nil)

			create, destroy, removeDeadRow, addDeadRow, err := rata.NeedToScaleHypervisors(context.Background(), tc.AvailHypers, tc.Hypers)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			assert.Equal(tc.ExpectedRemoveDeadRow, removeDeadRow)
			assert.Equal(tc.ExpectedCreateHypervisor, create)
			assert.Equal(tc.ExpectedAddDeadRow, addDeadRow)
			assert.Equal(tc.ExpectedDestroyHypervisor, destroy)
		})
	}
}

func TestRataExtraOperations(t *testing.T) {
	assert := assert.New(t)

	cases := map[string]struct {
		PrepareAPI  func(*apiMock.Client)
		Hypers      []*client.OrchestratorHypervisor
		HyperMinCPU int
		HyperMinRAM int
		HyperMaxRAM int
		ExpectedErr string
	}{
		"if there are enough resources, it shouldn't do anything": {
			PrepareAPI: func(c *apiMock.Client) {},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:     "first",
				Status: client.HypervisorStatusOffline,
				RAM: client.OrchestratorResourceLoad{
					Free: 10,
				},
			}, {
				ID:     "second",
				Status: client.HypervisorStatusOnline,
				RAM: client.OrchestratorResourceLoad{
					Free: 60,
				},
			}},
			HyperMinRAM: 50,
		},
		"if there's not enough RAM, it should set the hypervisor to only forced": {
			PrepareAPI: func(c *apiMock.Client) {
				c.Mock.On("AdminHypervisorOnlyForced", mock.AnythingOfType("*context.emptyCtx"), "second", true).Return(nil)
			},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:                  "first",
				Status:              client.HypervisorStatusOffline,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Free: 10,
				},
			}, {
				ID:                  "second",
				Status:              client.HypervisorStatusOnline,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Free: 30,
				},
			}},
			HyperMinRAM: 50,
		},
		"if there's too much free RAM, it should remove the hypervisor from only forced": {
			PrepareAPI: func(c *apiMock.Client) {
				c.Mock.On("AdminHypervisorOnlyForced", mock.AnythingOfType("*context.emptyCtx"), "second", false).Return(nil)
			},
			Hypers: []*client.OrchestratorHypervisor{{
				ID:                  "first",
				Status:              client.HypervisorStatusOffline,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Free: 10,
				},
			}, {
				ID:                  "second",
				OnlyForced:          true,
				Status:              client.HypervisorStatusOnline,
				OrchestratorManaged: true,
				RAM: client.OrchestratorResourceLoad{
					Free: 200,
				},
			}},
			HyperMinRAM: 50,
			HyperMaxRAM: 150,
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)
			api := &apiMock.Client{}

			tc.PrepareAPI(api)

			rata := director.NewRata(cfg.DirectorRata{
				HyperMinCPU: tc.HyperMinCPU,
				HyperMinRAM: tc.HyperMinRAM,
				HyperMaxRAM: tc.HyperMaxRAM,
			}, false, &log, api)

			err := rata.ExtraOperations(context.Background(), tc.Hypers)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			api.AssertExpectations(t)
		})
	}
}
