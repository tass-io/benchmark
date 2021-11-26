package main

import (
	"time"

	"github.com/aws/aws-lambda-go/lambda"
)

type Param struct {
	Name string `json:"name"`
}

type Output struct {
	Greeting  string `json:"greeting"`
	StartTime int64  `json:"startTime"`
}

func HandleRequest(p Param) (Output, error) {
	startTime := time.Now().UnixNano() / 1000000
	name := p.Name
	if p.Name == "" {
		name = "stranger"
	}
	res := Output{}
	res.Greeting = "Hello " + name + "!"
	res.StartTime = startTime
	return res, nil
}

func main() {
	lambda.Start(HandleRequest)
}
