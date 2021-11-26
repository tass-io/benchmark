package main

import (
	"time"
)

// nolint: unused
func Handler(parameters map[string]interface{}) (map[string]interface{}, error) {
	depth := int(parameters["depth"].(float64)) + 1
	path := parameters["path"].([]interface{}) // string
	exec := parameters["exec"].([]interface{}) // float64
	time.Sleep(time.Millisecond * time.Duration(int64((exec[depth].(float64)))))
	return map[string]interface{}{"path": path, "exec": exec, "depth": depth, "next": path[depth].(string)}, nil
}
