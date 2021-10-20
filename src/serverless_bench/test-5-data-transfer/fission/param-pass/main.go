package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"time"
)

type param struct {
	Payload string `json:"payload"`
	Rettime int64  `json:"retTime"`
}

// nolint: unused
func Handler(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now().UnixMilli()
	reqBody, err := ioutil.ReadAll(r.Body)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		w.Write([]byte(err.Error()))
		return
	}
	p := param{}
	err = json.Unmarshal(reqBody, &p)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		w.Write([]byte(err.Error()))
		return
	}
	payload := p.Payload
	retTime := p.Rettime
	res := map[string]interface{}{}
	if p.Rettime == 0 {
		fmt.Println("chain head with payload size: ", len(payload))
		res = map[string]interface{}{"payload": payload, "retTime": time.Now().UnixMilli()}

	} else {
		comTime := startTime - retTime
		fmt.Println("payload size:", len(payload))
		res = map[string]interface{}{"retTime": time.Now().UnixMilli(), "startTime": startTime, "comTime": comTime}
	}
	rb, err := json.Marshal(res)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}
	w.WriteHeader(http.StatusOK)
	w.Header().Set("Content-Type", "application/json")
	_, err = w.Write(rb)
	if err != nil {
		panic(err)
	}
}
