package director

import (
	"context"

	"gitlab.com/isard/isardvdi/orchestrator/model"
	operationsv1 "gitlab.com/isard/isardvdi/pkg/gen/proto/go/operations/v1"
)

var Available = []string{DirectorTypeRata}

type Director interface {
	// NeedToScaleHypervisors states if there's a scale needed to be done.
	NeedToScaleHypervisors(ctx context.Context, hypers []*model.Hypervisor) (*operationsv1.CreateHypervisorRequest, *operationsv1.DestroyHypervisorRequest, error)
	// ExtraOperations is a place for running infrastructure operations that don't fit in the other functions but are required
	ExtraOperations(ctx context.Context, hypers []*model.Hypervisor) error
	String() string
}
