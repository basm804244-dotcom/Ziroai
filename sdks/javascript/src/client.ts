import axios, { AxiosInstance } from 'axios';

export class AetherAIClient {
  private client: AxiosInstance;
  public apiKey: string;
  public baseURL: string;

  constructor(options: { apiKey?: string; baseURL?: string; timeout?: number } = {}) {
    this.apiKey = options.apiKey || this.getApiKeyFromEnv();
    this.baseURL = (options.baseURL || 'https://api.aether.ai').replace(/\/$/, '');
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: options.timeout || 60000,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'X-Client-Version': '2026.7.0',
      },
    });
  }

  private getApiKeyFromEnv(): string {
    if (typeof process !== 'undefined' && process.env) {
      const key = process.env.AETHERAI_API_KEY;
      if (key) return key;
    }
    throw new Error('AETHERAI_API_KEY not found');
  }

  async chat(messages: any[], model: string = 'gpt-4o', stream: boolean = false) {
    const response = await this.client.post('/models/chat', { model_id: model, messages, stream });
    return response.data;
  }

  async listModels() {
    const response = await this.client.get('/models');
    return response.data;
  }

  async createAgent(name: string, description: string, systemPrompt: string) {
    const response = await this.client.post('/agents', { name, description, system_prompt: systemPrompt });
    return response.data;
  }
}
