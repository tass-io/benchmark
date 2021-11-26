package main

import "time"

func Main(obj map[string]interface{}) map[string]interface{} {
	depth := int(obj["depth"].(float64)) + 1
	path := obj["path"].([]interface{}) // string
	exec := obj["exec"].([]interface{}) // float64
	time.Sleep(time.Millisecond * time.Duration(int64((exec[depth].(float64)))))
	return map[string]interface{}{"path": path, "exec": exec, "depth": depth, "next": path[depth].(string)}
}
