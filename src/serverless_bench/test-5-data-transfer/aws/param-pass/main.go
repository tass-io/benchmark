package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
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
	// Configure to use S3 Server
	s3Config := &aws.Config{
		Credentials:      credentials.NewStaticCredentials("AKIAZN7TGKLZYHVHFUVJ", "jnPoZRjS5fQMHXQWhyJQapiC8E2eACGGOdncViRc", ""),
		Region:           aws.String("cn-northwest-1"),
		DisableSSL:       aws.Bool(true),
		S3ForcePathStyle: aws.Bool(false), //virtual-host style方式，不要修改
	}
	newSession := session.New(s3Config)
	s3Client := s3.New(newSession)
	cparams := &s3.HeadBucketInput{
		Bucket: aws.String("awsfaas"), // Required
	}
	_, err := s3Client.HeadBucket(cparams)
	if err != nil {
		return err
	}
	uploader := s3manager.NewUploader(newSession)
	// write json to file
	b, err := json.Marshal(j)
	if err != nil {
		return err
	}
	err = ioutil.WriteFile("."+filename, b, 0666)
	if err != nil {
		return err
	}
	f, err := os.Open("." + filename)
	if err != nil {
		return err
	}
	defer f.Close()
	// Upload the file to S3.
	result, err := uploader.Upload(&s3manager.UploadInput{
		Bucket:      aws.String("awsfaas"),
		Key:         aws.String(filename),
		Body:        f,
		ContentType: aws.String("application/zip"),
		ACL:         aws.String("public-read"),
	}, func(u *s3manager.Uploader) {
		u.PartSize = 10 * 1024 * 1024 // 分块大小,当文件体积超过10M开始进行分块上传
		u.LeavePartsOnError = true
		u.Concurrency = 3
	}) //并发数
	fmt.Println(result)
	if err != nil {
		return err
	}
	return nil
}

func download_json(down_file string) (map[string]interface{}, error) {
	// Configure to use S3 Server
	s3Config := &aws.Config{
		Credentials:      credentials.NewStaticCredentials("AKIAZN7TGKLZYHVHFUVJ", "jnPoZRjS5fQMHXQWhyJQapiC8E2eACGGOdncViRc", ""),
		Region:           aws.String("cn-northwest-1"),
		DisableSSL:       aws.Bool(true),
		S3ForcePathStyle: aws.Bool(false), //virtual-host style方式，不要修改
	}
	newSession := session.New(s3Config)
	s3Client := s3.New(newSession)
	cparams := &s3.HeadBucketInput{
		Bucket: aws.String("awsfaas"), // Required
	}
	_, err := s3Client.HeadBucket(cparams)
	if err != nil {
		return nil, err
	}
	file, err := os.Create("." + down_file)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	downloader := s3manager.NewDownloader(newSession)
	numBytes, err := downloader.Download(file,
		&s3.GetObjectInput{
			Bucket: aws.String("awsfaas"),
			Key:    aws.String(down_file),
		})
	if err != nil {
		return nil, err
	}
	fmt.Println("Downloaded file", file.Name(), numBytes, "bytes")
	b, err := ioutil.ReadFile("." + down_file)
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
		fmt.Println("chain head with payload size: ", len(payload))
		if payload == "s3" {
			// download param from s3
			json, err := download_json("/param0")
			if err != nil {
				return Output{}, nil
			}
			payload = json["payload"].(string)
			// upload param to s3
			err = upload_json(map[string]string{"payload": payload}, "/param1")
			if err != nil {
				return Output{}, nil
			}
			// reset param
			payload = "s3"
		}
		res = Output{Payload: payload, RetTime: time.Now().UnixNano() / 1000000}
	} else {
		if payload == "s3" {
			// download param from s3
			json, err := download_json("/param1")
			if err != nil {
				return Output{}, nil
			}
			payload = json["payload"].(string)
			// upload param to s3
			err = upload_json(map[string]string{"payload": payload}, "/param2")
			if err != nil {
				return Output{}, nil
			}
		}
		comTime := startTime - retTime
		fmt.Println("payload size:", len(payload))
		res = Output{RetTime: time.Now().UnixNano() / 1000000, StartTime: startTime, ComTime: comTime}
	}
	return res, nil
}

func main() {
	lambda.Start(HandleRequest)
}
