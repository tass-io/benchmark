package main

import (
	"time"

	"github.com/aws/aws-lambda-go/lambda"
)

type Param struct {
	N          int     `json:"n"`
	StartTimes []int64 `json:"startTimes"`
	RetTimes   []int64 `json:"retTimes"`
}

type Output struct {
	N          int     `json:"n"`
	StartTimes []int64 `json:"startTimes"`
	RetTimes   []int64 `json:"retTimes"`
}

func HandleRequest(p Param) (Output, error) {
	startTime := time.Now().UnixNano() / 1000000
	startTimes := []int64{}
	retTimes := []int64{}
	var res Output
	n := 1 + p.N
	startTimes = append(startTimes, startTime)
	if len(p.StartTimes) != 0 {
		startTimes = append(startTimes, p.StartTimes...)
	}
	if len(p.RetTimes) != 0 {
		retTimes = append(retTimes, p.RetTimes...)
		retTimes = append(retTimes, time.Now().UnixNano()/1000000)
		res = Output{N: n, StartTimes: startTimes, RetTimes: retTimes}
	} else {
		retTimes = append(retTimes, time.Now().UnixNano()/1000000)
		res = Output{N: n, StartTimes: startTimes, RetTimes: retTimes}
	}
	return res, nil
}

func main() {
	lambda.Start(HandleRequest)
}
