package main

import (
	"fmt"
	"time"
)

// nolint: unused
func Main(obj map[string]interface{}) map[string]interface{} {
	startTime := time.Now().UnixMilli()
	payload := obj["payload"].(string)
	if rt, ok := obj["retTime"].(float64); ok {
		comTime := startTime - int64(rt)
		fmt.Println("payload size:", len(payload))
		return map[string]interface{}{"retTime": time.Now().UnixMilli(), "startTime": startTime, "comTime": comTime}
	} else {
		fmt.Println("chain head with payload size: ", len(payload))
		return map[string]interface{}{"payload": payload, "retTime": time.Now().UnixMilli()}
	}
}
