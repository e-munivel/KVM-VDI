package migrations

import (
	"fmt"

	"github.com/go-pg/migrations/v8"
	"github.com/go-pg/pg/v10/orm"
)

func init() {
	// Don't pluralize tables and set prefix
	orm.SetTableNameInflector(func(s string) string {
		return "isardvdi_" + s
	})
}

func Run(db migrations.DB) error {
	migrations.SetTableName("isardvdi_gopg_migration")
	old, new, err := migrations.Run(db, "init")
	if err != nil {
		return fmt.Errorf("initialize db migrations system: %w", err)
	}

	fmt.Printf("migrated from %d to %d\n", old, new)

	old, new, err = migrations.Run(db)
	if err != nil {
		return fmt.Errorf("run the db migrations: %w", err)
	}

	fmt.Printf("migrated from %d to %d\n", old, new)

	return nil
}
