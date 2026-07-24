package aetherai

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

type Client struct {
	APIKey  string
	BaseURL string
	HTTP    *http.Client
}

func NewClient(apiKey string) *Client {
	if apiKey == "" {
		apiKey = os.Getenv("AETHERAI_API_KEY")
	}
	return &Client{
		APIKey:  apiKey,
		BaseURL: "https://api.aether.ai",
		HTTP:    &http.Client{Timeout: 60 * time.Second},
	}
}

func (c *Client) Chat(messages []map[string]string, model string) (map[string]interface{}, error) {
	payload := map[string]interface{}{"model_id": model, "messages": messages, "stream": false}
	body, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", c.BaseURL+"/api/v1/models/chat", bytes.NewBuffer(body))
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return result, nil
}
