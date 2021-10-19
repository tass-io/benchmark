package main

import (
	"fmt"
	"time"
)

// nolint: unused
func Handler(parameters map[string]interface{}) (map[string]interface{}, error) {
	startTime := time.Now().UnixMilli()
	payload := parameters["payload"].(string)
	if rt, ok := parameters["retTime"].(float64); ok {
		comTime := startTime - int64(rt)
		fmt.Println("payload size:", len(payload))
		return map[string]interface{}{"retTime": time.Now().UnixMilli(), "startTime": startTime, "comTime": comTime}, nil
	} else {
		fmt.Println("chain head with payload size: ", len(payload))
		return map[string]interface{}{"payload": payload, "retTime": time.Now().UnixMilli()}, nil
	}
}
