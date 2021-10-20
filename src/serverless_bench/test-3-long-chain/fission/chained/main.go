package main

import (
	"encoding/json"
	"io/ioutil"
	"net/http"
	"time"
)

type param struct {
	N          int     `json:"n"`
	StartTimes []int64 `json:"startTimes"`
	RetTimes   []int64 `json:"retTimes"`
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
	startTimes := []int64{}
	retTimes := []int64{}
	res := map[string]interface{}{}
	n := 1 + p.N
	startTimes = append(startTimes, startTime)
	if len(p.StartTimes) != 0 {
		startTimes = append(startTimes, p.StartTimes...)
	}
	if len(p.RetTimes) != 0 {
		retTimes = append(retTimes, p.RetTimes...)
		retTimes = append(retTimes, time.Now().UnixMilli())
		res = map[string]interface{}{"n": n, "startTimes": startTimes, "retTimes": retTimes}
	} else {
		retTimes = append(retTimes, time.Now().UnixMilli())
		res = map[string]interface{}{"n": n, "startTimes": startTimes, "retTimes": retTimes}
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
