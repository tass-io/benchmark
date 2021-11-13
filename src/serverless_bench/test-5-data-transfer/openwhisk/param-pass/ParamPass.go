package main

import (
	"fmt"
	"time"
)

// nolint: unused
func Main(obj map[string]interface{}) map[string]interface{} {
	startTime := time.Now().UnixNano() / 1000000
	payload := obj["payload"].(string)
	if rt, ok := obj["retTime"].(float64); ok {
		comTime := startTime - int64(rt)
		fmt.Println("payload size:", len(payload))
		return map[string]interface{}{"payload": payload, "retTime": time.Now().UnixNano() / 1000000, "startTime": startTime, "comTime": comTime}
	} else {
		fmt.Println("chain head with payload size: ", len(payload))
		return map[string]interface{}{"payload": payload, "retTime": time.Now().UnixNano() / 1000000}
	}
}
