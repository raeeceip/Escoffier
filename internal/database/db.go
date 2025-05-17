package database

import (
	"github.com/jinzhu/gorm"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

var DB *gorm.DB

// InitDB initializes the database connection
func InitDB(dbPath string) error {
	var err error
	DB, err = gorm.Open("sqlite3", dbPath)
	if err != nil {
		return err
	}
	return nil
}

// GetDB returns the database instance
func GetDB() *gorm.DB {
	return DB
}

// CloseDB closes the database connection
func CloseDB() error {
	if DB != nil {
		return DB.Close()
	}
	return nil
}
