package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unsafe"
)

var (
	pid    int
	memory []byte
)

const (
	memCDFFilename  = "CDFs/memCDF.csv"
	execCDFFilename = "CDFs/execTimeCDF.csv"
	// mimic C program Macros
	KILO_BYTE         = 1024
	MEGA_BYTE         = ((KILO_BYTE) * (KILO_BYTE))
	PLACEHOLDERZYGOTE = "0123456789"
	PLACEHOLDER_LEN   = 100
)

type param struct {
	Sequence int `json:"sequence"`
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
	var sequence int
	if p.Sequence != 0 {
		sequence = p.Sequence + 1
	}

	mmStartTime := time.Now().UnixMilli()
	memSize := mallocRandMem()
	mmEndTime := time.Now().UnixMilli()
	mmExecTime := mmEndTime - mmStartTime

	execTime := execRandTime(mmExecTime)
	// Prevent Golang GC process
	fmt.Print(memory[0])
	res := map[string]interface{}{"sequence": sequence, "startTime": startTime, "memSize": memSize, "execTime": execTime}
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

func mallocRandMem() int {
	filename := baseFilename() + memCDFFilename
	bias := 2 // The Golang Program memory usage
	randMem := getRandValueRefByCDF(filename) - bias
	fmt.Printf("Alloc random memory: %v\n", randMem)
	// mimic C program calling
	allocMem(randMem)
	return randMem
}

func execRandTime(mmExecTime int64) int64 {
	filename := baseFilename() + execCDFFilename
	randExecTime := int64(getRandValueRefByCDF(filename))

	exactAluTime := randExecTime - mmExecTime
	if exactAluTime > 0 {
		alu(exactAluTime)
	}
	fmt.Printf("Execute random time: %v\n", randExecTime)
	return randExecTime
}

// =====================  From C program ============================
// Alloc Mem. Rewrite From ServerlessBench C Program
func allocMem(randMem int) {
	memSize := randMem * MEGA_BYTE
	memory = make([]byte, memSize)
	placeholder := generatePlaceholder()
	for i := 0; i < memSize-PLACEHOLDER_LEN; i += PLACEHOLDER_LEN {
		copy(memory[i:], placeholder)
	}
	fmt.Printf("Alloc %d bytes memory\n", memSize)
}

func generatePlaceholder() []byte {
	placeholderzygote := []byte(PLACEHOLDERZYGOTE)
	placeholder := make([]byte, PLACEHOLDER_LEN)
	for i := 0; i < PLACEHOLDER_LEN/len(placeholderzygote); i++ {
		placeholder = append(placeholder, placeholderzygote...)
	}
	return placeholder
}

// ===================================================================

// ===================== From utils ==================================
func getRandValueRefByCDF(filename string) int {
	content, err := ioutil.ReadFile(filename)
	if err != nil {
		panic(err)
	}
	contentS := *(*string)(unsafe.Pointer(&content))
	values := []int{}
	P := []float64{}
	fCDF := strings.Split(contentS, "\n")
	for _, line := range fCDF {
		lineSplit := strings.Split(line, ",")
		if value, err := strconv.Atoi(lineSplit[0]); err != nil {
			panic(err)
		} else {
			values = append(values, value)
		}
		if p, err := strconv.ParseFloat(lineSplit[1], 64); err != nil {
			panic(err)
		} else {
			P = append(P, p)
		}
	}
	rand.Seed(time.Now().Unix())
	randP := rand.Float64()
	randValue := values[binarySearch(P, randP)]
	return randValue
}

func binarySearch(nums []float64, target float64) int {
	upper := len(nums) - 1
	lower := 0
	var mid int
	for lower <= upper {
		mid = int((upper + lower) / 2)
		if target > nums[mid] {
			lower = mid + 1
		} else if target < nums[mid-1] {
			upper = mid - 1
		} else {
			return mid
		}
	}
	return mid
}

func alu(times int64) int64 {
	startTime := time.Now().UnixMilli()
	rand.Seed(time.Now().Unix())
	base := 10000
	a := int64(10 + rand.Intn(90))
	b := int64(10 + rand.Intn(90))
	temp := int64(0)
	for {
		for i := 0; i < base; i++ {
			if i%4 == 0 {
				temp = a + b
			} else if i%4 == 1 {
				temp = a - b
			} else if i%4 == 2 {
				temp = a * b
			} else {
				temp = a / b
			}
		}
		endTime := time.Now().UnixMilli()
		if endTime-startTime > times {
			break
		}
	}
	return temp
}

// ===================================================================

func baseFilename() string {
	return "./"
}
