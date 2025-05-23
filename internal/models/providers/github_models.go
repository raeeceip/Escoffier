package providers

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/openai"
)

// GitHubModelsProvider implements the Provider interface for GitHub Models
type GitHubModelsProvider struct {
	client *openai.LLM
}

// NewGitHubModelsProvider creates a new GitHub Models provider
func NewGitHubModelsProvider() (*GitHubModelsProvider, error) {
	token := os.Getenv("GITHUB_TOKEN")
	if token == "" {
		return nil, fmt.Errorf("GITHUB_TOKEN environment variable is required for GitHub Models")
	}

	// GitHub Models uses an OpenAI-compatible API
	opts := []openai.Option{
		openai.WithToken(token),
		openai.WithBaseURL("https://models.inference.ai.azure.com"),
	}

	client, err := openai.New(opts...)
	if err != nil {
		return nil, fmt.Errorf("failed to create GitHub Models client: %w", err)
	}

	return &GitHubModelsProvider{client: client}, nil
}

// Name returns the provider name
func (p *GitHubModelsProvider) Name() string {
	return "github_models"
}

// ListModels returns available models
func (p *GitHubModelsProvider) ListModels(ctx context.Context) ([]ModelInfo, error) {
	// GitHub Models supports these models for free
	return []ModelInfo{
		{ID: "gpt-4o-mini", Name: "GPT-4o Mini", Provider: "github_models", MaxTokens: 128000},
		{ID: "gpt-4o", Name: "GPT-4o", Provider: "github_models", MaxTokens: 128000},
		{ID: "Phi-3.5-mini-instruct", Name: "Phi 3.5 Mini", Provider: "github_models", MaxTokens: 8192},
		{ID: "Meta-Llama-3.1-70B-Instruct", Name: "Llama 3.1 70B", Provider: "github_models", MaxTokens: 8192},
		{ID: "Meta-Llama-3.1-405B-Instruct", Name: "Llama 3.1 405B", Provider: "github_models", MaxTokens: 8192},
		{ID: "Mistral-large-2407", Name: "Mistral Large", Provider: "github_models", MaxTokens: 32000},
		{ID: "AI21-Jamba-1.5-Large", Name: "Jamba 1.5 Large", Provider: "github_models", MaxTokens: 8192},
	}, nil
}

// CreateCompletion generates a completion
func (p *GitHubModelsProvider) CreateCompletion(ctx context.Context, req CompletionRequest) (*CompletionResponse, error) {
	opts := []llms.CallOption{
		llms.WithMaxTokens(req.MaxTokens),
		llms.WithTemperature(req.Temperature),
		llms.WithModel(req.Model),
	}

	response, err := p.client.GenerateContent(ctx, []llms.MessageContent{
		llms.TextParts(llms.ChatMessageTypeHuman, req.Prompt),
	}, opts...)

	if err != nil {
		return nil, fmt.Errorf("failed to generate completion: %w", err)
	}

	if response == nil || len(response.Choices) == 0 {
		return nil, fmt.Errorf("empty response from GitHub Models")
	}

	return &CompletionResponse{
		Text: response.Choices[0].Content,
		Metadata: map[string]interface{}{
			"model":  req.Model,
			"tokens": response.Usage,
		},
	}, nil
}

// CreateChatCompletion generates a chat completion
func (p *GitHubModelsProvider) CreateChatCompletion(ctx context.Context, req ChatCompletionRequest) (*ChatCompletionResponse, error) {
	messages := make([]llms.MessageContent, len(req.Messages))
	for i, msg := range req.Messages {
		var msgType llms.ChatMessageType
		switch msg.Role {
		case "system":
			msgType = llms.ChatMessageTypeSystem
		case "assistant":
			msgType = llms.ChatMessageTypeAI
		default:
			msgType = llms.ChatMessageTypeHuman
		}
		messages[i] = llms.TextParts(msgType, msg.Content)
	}

	opts := []llms.CallOption{
		llms.WithMaxTokens(req.MaxTokens),
		llms.WithTemperature(req.Temperature),
		llms.WithModel(req.Model),
	}

	if req.Stream {
		opts = append(opts, llms.WithStreamingFunc(req.StreamingFunc))
	}

	response, err := p.client.GenerateContent(ctx, messages, opts...)
	if err != nil {
		return nil, fmt.Errorf("failed to generate chat completion: %w", err)
	}

	if response == nil || len(response.Choices) == 0 {
		return nil, fmt.Errorf("empty response from GitHub Models")
	}

	responseMessages := make([]ChatMessage, len(response.Choices))
	for i, choice := range response.Choices {
		responseMessages[i] = ChatMessage{
			Role:    "assistant",
			Content: choice.Content,
		}
	}

	return &ChatCompletionResponse{
		Messages: responseMessages,
		Metadata: map[string]interface{}{
			"model":  req.Model,
			"tokens": response.Usage,
		},
	}, nil
}

// CreateEmbedding generates embeddings
func (p *GitHubModelsProvider) CreateEmbedding(ctx context.Context, req EmbeddingRequest) (*EmbeddingResponse, error) {
	// GitHub Models doesn't support embeddings in the free tier
	return nil, fmt.Errorf("embeddings are not supported by GitHub Models free tier")
}

// GetModel returns the underlying LLM
func (p *GitHubModelsProvider) GetModel(modelID string) (llms.Model, error) {
	return p.client, nil
}

// HealthCheck verifies the provider is working
func (p *GitHubModelsProvider) HealthCheck(ctx context.Context) error {
	// Try a simple completion
	_, err := p.CreateCompletion(ctx, CompletionRequest{
		Model:       "gpt-4o-mini",
		Prompt:      "Hello",
		MaxTokens:   5,
		Temperature: 0,
	})
	return err
}

// GetUsage returns usage information
func (p *GitHubModelsProvider) GetUsage(ctx context.Context) (map[string]interface{}, error) {
	// GitHub Models doesn't provide usage API in free tier
	return map[string]interface{}{
		"provider": "github_models",
		"tier":     "free",
		"note":     "Usage tracking not available in free tier",
	}, nil
}

// GetRateLimits returns rate limit information
func (p *GitHubModelsProvider) GetRateLimits() map[string]interface{} {
	return map[string]interface{}{
		"requests_per_minute": 15,
		"tokens_per_minute":   40000,
		"note":                "GitHub Models free tier limits",
	}
}

// StreamCompletion streams a completion response
func (p *GitHubModelsProvider) StreamCompletion(ctx context.Context, req CompletionRequest, callback func(string) error) error {
	req.StreamingFunc = func(ctx context.Context, chunk []byte) error {
		return callback(string(chunk))
	}
	
	_, err := p.CreateCompletion(ctx, req)
	return err
}

// MarshalJSON implements json.Marshaler
func (p *GitHubModelsProvider) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]string{
		"type":     "github_models",
		"provider": p.Name(),
	})
}