package main

import (
	"time"

	"github.com/aws/aws-lambda-go/lambda"
)

type Param struct {
	Depth int       `json:"depth"`
	Path  []string  `json:"path"`
	Exec  []float64 `json:"exec"`
}

type Output struct {
	Depth int       `json:"depth"`
	Path  []string  `json:"path"`
	Exec  []float64 `json:"exec"`
	Next  string    `json:"next"`
}

func HandleRequest(p Param) (Output, error) {
	p.Depth += 1
	time.Sleep(time.Millisecond * time.Duration(int64((p.Exec[p.Depth]))))
	return Output{Path: p.Path, Exec: p.Exec, Depth: p.Depth, Next: p.Path[p.Depth]}, nil
}

func main() {
	lambda.Start(HandleRequest)
}
