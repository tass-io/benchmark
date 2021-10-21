package main

import "time"

// nolint: unused
func Handler(parameters map[string]interface{}) (map[string]interface{}, error) {
	startTime := time.Now().UnixNano() / 1000000
	name := "stranger"
	Pname, ok := parameters["name"].(string)
	if ok {
		name = Pname
	}
	res := map[string]interface{}{}
	res["greeting"] = "Hello " + name + "!"
	res["startTime"] = startTime
	return res, nil
}
