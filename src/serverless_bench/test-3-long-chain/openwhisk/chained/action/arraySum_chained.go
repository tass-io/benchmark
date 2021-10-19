package main

import "time"

// nolint: unused
func Main(obj map[string]interface{}) map[string]interface{} {
	startTime := time.Now().UnixMilli()
	n := 1 + int(obj["n"].(float64))
	startTimes := []int64{}
	retTimes := []int64{}
	startTimes = append(startTimes, startTime)
	if sts, ok := obj["startTimes"].([]interface{}); ok {
		for _, st := range sts {
			startTimes = append(startTimes, int64(st.(float64)))
		}
	}
	if rts, ok := obj["retTimes"].([]interface{}); ok {
		for _, rt := range rts {
			retTimes = append(retTimes, int64(rt.(float64)))
		}
		retTimes = append(retTimes, time.Now().UnixMilli())
		return map[string]interface{}{"n": n, "startTimes": startTimes, "retTimes": retTimes}
	} else {
		retTimes = append(retTimes, time.Now().UnixMilli())
		return map[string]interface{}{"n": n, "startTimes": startTimes, "retTimes": retTimes}
	}
}
