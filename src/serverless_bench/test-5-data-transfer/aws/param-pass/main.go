package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/s3/s3manager"
)

type Param struct {
	Payload string `json:"payload"`
	Rettime int64  `json:"retTime"`
}

type Output struct {
	Payload   string `json:"payload"`
	RetTime   int64  `json:"retTime"`
	StartTime int64  `json:"startTime"`
	ComTime   int64  `json:"comTime"`
}

func upload_json(j map[string]string, filename string) error {
	// write json to file
	b, err := json.Marshal(j)
	if err != nil {
		return err
	}
	err = ioutil.WriteFile("/tmp"+filename, b, 0666)
	if err != nil {
		return err
	}
	// Upload the file to S3.
	f, err := os.Open("/tmp" + filename)
	if err != nil {
		return err
	}
	defer f.Close()
	sess := session.Must(session.NewSession())
	uploader := s3manager.NewUploader(sess)
	_, err = uploader.Upload(&s3manager.UploadInput{
		Bucket: aws.String("params"),
		Key:    aws.String(filename),
		Body:   f,
	})
	if err != nil {
		return fmt.Errorf("failed to upload file, %v", err)
	}
	return nil
}

func download_json(down_file string) (map[string]interface{}, error) {
	// The session the S3 Downloader will use
	sess := session.Must(session.NewSession())

	// Create a downloader with the session and default options
	downloader := s3manager.NewDownloader(sess)

	// Create a file to write the S3 Object contents to.
	f, err := os.Create("/tmp" + down_file)
	if err != nil {
		return nil, fmt.Errorf("failed to create file %q, %v", "/tmp"+down_file, err)
	}

	// Write the contents of S3 Object to the file
	n, err := downloader.Download(f, &s3.GetObjectInput{
		Bucket: aws.String("params"),
		Key:    aws.String(down_file),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to download file, %v", err)
	}
	f.Close()
	fmt.Printf("file downloaded, %d bytes\n", n)
	b, err := ioutil.ReadFile("/tmp" + down_file)
	if err != nil {
		return nil, err
	}
	var res map[string]interface{}
	err = json.Unmarshal(b, &res)
	if err != nil {
		return nil, err
	}
	return res, nil
}

func HandleRequest(p Param) (Output, error) {
	startTime := time.Now().UnixNano() / 1000000
	payload := p.Payload
	retTime := p.Rettime
	var res Output
	if p.Rettime == 0 {
		if payload == "s3" {
			// download param from s3
			json, err := download_json("/param0")
			if err != nil {
				return Output{Payload: err.Error()}, nil
			}
			payload = json["payload"].(string)
			fmt.Println("chain head with payload size: ", len(payload))
			// upload param to s3
			err = upload_json(map[string]string{"payload": payload}, "/param1")
			if err != nil {
				return Output{Payload: err.Error()}, nil
			}
			// reset param
			payload = "s3"
		} else {
			fmt.Println("chain head with payload size: ", len(payload))
		}
		res = Output{Payload: payload, RetTime: time.Now().UnixNano() / 1000000}
	} else {
		if payload == "s3" {
			// download param from s3
			json, err := download_json("/param1")
			if err != nil {
				return Output{Payload: payload}, nil
			}
			payload = json["payload"].(string)
			fmt.Println("payload size:", len(payload))
			// upload param to s3
			err = upload_json(map[string]string{"payload": payload}, "/param2")
			if err != nil {
				return Output{Payload: payload}, nil
			}
			payload = "s3"
		} else {
			fmt.Println("payload size:", len(payload))
		}
		comTime := startTime - retTime
		res = Output{Payload: payload, RetTime: time.Now().UnixNano() / 1000000, StartTime: startTime, ComTime: comTime}
	}
	return res, nil
}

func main() {
	lambda.Start(HandleRequest)
}
