package com.aetherai.sdk;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public class AetherAIClient {
    private final String apiKey;
    private final String baseUrl;
    private final HttpClient httpClient;

    public AetherAIClient(String apiKey) {
        this.apiKey = apiKey != null ? apiKey : System.getenv("AETHERAI_API_KEY");
        this.baseUrl = "https://api.aether.ai";
        this.httpClient = HttpClient.newHttpClient();
    }

    public String chat(String messages, String model) throws Exception {
        String json = String.format("{\"model_id\":\"%s\",\"messages\":%s,\"stream\":false}", model, messages);
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/v1/models/chat"))
            .header("Authorization", "Bearer " + apiKey)
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }
}
