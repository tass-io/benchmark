package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	redis "github.com/go-redis/redis/v8"
)

func get_json(key string) (map[string]interface{}, error) {
	rdb := redis.NewClient(&redis.Options{
		Addr:     "redis.default.svc.cluster.local:6379",
		Password: "", // no password set
		DB:       0,  // use default DB
	})
	val, err := rdb.Get(context.Background(), key).Result()
	if err != nil {
		return nil, err
	}
	res := map[string]interface{}{}
	err = json.Unmarshal([]byte(val), &res)
	if err != nil {
		return nil, err
	}
	return res, nil
}

func set_json(j map[string]interface{}, key string) error {
	rdb := redis.NewClient(&redis.Options{
		Addr:     "redis.default.svc.cluster.local:6379",
		Password: "", // no password set
		DB:       0,  // use default DB
	})
	b, err := json.Marshal(j)
	if err != nil {
		return err
	}
	err = rdb.Set(context.Background(), key, string(b), 0).Err()
	if err != nil {
		return err
	}
	return nil
}

// nolint: unused
func Main(obj map[string]interface{}) map[string]interface{} {
	startTime := time.Now().UnixNano() / 1000000
	payload := obj["payload"].(string)
	if rt, ok := obj["retTime"].(float64); ok {
		if payload == "redis" {
			// get param from redis
			json, err := get_json("param1")
			if err != nil {
				return map[string]interface{}{"payload": err.Error()}
			}
			payload = json["payload"].(string)
			fmt.Println("payload size:", len(payload))
			// set param to redis
			err = set_json(map[string]interface{}{"payload": payload}, "param2")
			if err != nil {
				return map[string]interface{}{"payload": err.Error()}
			}
			// reset param
			payload = "redis"
		} else {
			fmt.Println("payload size:", len(payload))
		}
		comTime := startTime - int64(rt)
		return map[string]interface{}{"payload": payload, "retTime": time.Now().UnixNano() / 1000000, "startTime": startTime, "comTime": comTime}
	} else {
		if payload == "redis" {
			// get param from redis
			json, err := get_json("param0")
			if err != nil {
				return map[string]interface{}{"payload": err.Error()}
			}
			payload = json["payload"].(string)
			fmt.Println("chain head with payload size: ", len(payload))
			// set param to redis
			err = set_json(map[string]interface{}{"payload": payload}, "param1")
			if err != nil {
				return map[string]interface{}{"payload": err.Error()}
			}
			// reset param
			payload = "redis"
		} else {
			fmt.Println("chain head with payload size: ", len(payload))
		}
		return map[string]interface{}{"payload": payload, "retTime": time.Now().UnixNano() / 1000000}
	}
}

