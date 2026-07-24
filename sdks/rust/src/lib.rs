use reqwest;
use serde_json::json;
use std::env;

pub struct Client {
    api_key: String,
    base_url: String,
    client: reqwest::Client,
}

impl Client {
    pub fn new(api_key: Option<String>) -> Self {
        let key = api_key.unwrap_or_else(|| env::var("AETHERAI_API_KEY").expect("AETHERAI_API_KEY not set"));
        Client {
            api_key: key,
            base_url: "https://api.aether.ai".to_string(),
            client: reqwest::Client::new(),
        }
    }

    pub async fn chat(&self, messages: Vec<serde_json::Value>, model: &str) -> Result<serde_json::Value, reqwest::Error> {
        let payload = json!({"model_id": model, "messages": messages, "stream": false});
        let res = self.client
            .post(&format!("{}/api/v1/models/chat", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&payload)
            .send()
            .await?;
        res.json().await
    }
}
