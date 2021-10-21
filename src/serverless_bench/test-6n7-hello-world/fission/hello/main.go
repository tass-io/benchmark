package main

import (
	"encoding/json"
	"io/ioutil"
	"net/http"
	"time"
)

type param struct {
	Name string `json:"name"`
}

// nolint: unused
func Handler(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now().UnixNano() / 1000000
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
	name := p.Name
	if p.Name == "" {
		name = "stranger"
	}
	res := map[string]interface{}{}
	res["greeting"] = "Hello " + name + "!"
	res["startTime"] = startTime
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
