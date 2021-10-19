package main

import "time"

// nolint: unused
func Main(obj map[string]interface{}) map[string]interface{} {
	startTime := time.Now().UnixMilli()
	name := "stranger"
	Pname, ok := obj["name"].(string)
	if ok {
		name = Pname
	}
	res := map[string]interface{}{}
	res["greeting"] = "Hello " + name + "!"
	res["startTime"] = startTime
	return res
}
