package providers

import (
	"context"
	"fmt"
	"os"

	"github.com/Azure/azure-sdk-for-go/sdk/ai/azopenai"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/to"
)

// AzureOpenAIProvider implements the Provider interface for Azure OpenAI
type AzureOpenAIProvider struct {
	client         *azopenai.Client
	deploymentName string
	temperature    float32
	maxTokens      int32
}

// NewAzureOpenAIProvider creates a new Azure OpenAI provider
func NewAzureOpenAIProvider() (*AzureOpenAIProvider, error) {
	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")
	apiKey := os.Getenv("AZURE_OPENAI_API_KEY")
	deploymentName := os.Getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

	if endpoint == "" || apiKey == "" || deploymentName == "" {
		return nil, fmt.Errorf("Azure OpenAI configuration missing: ensure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME are set")
	}

	keyCredential := azcore.NewKeyCredential(apiKey)
	client, err := azopenai.NewClientWithKeyCredential(endpoint, keyCredential, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create Azure OpenAI client: %w", err)
	}

	return &AzureOpenAIProvider{
		client:         client,
		deploymentName: deploymentName,
		temperature:    0.7,
		maxTokens:      2000,
	}, nil
}

// Complete implements the Provider interface
func (p *AzureOpenAIProvider) Complete(ctx context.Context, messages []Message) (string, error) {
	chatMessages := make([]azopenai.ChatRequestMessageClassification, len(messages))
	
	for i, msg := range messages {
		switch msg.Role {
		case "system":
			chatMessages[i] = &azopenai.ChatRequestSystemMessage{
				Content: to.Ptr(msg.Content),
			}
		case "user":
			chatMessages[i] = &azopenai.ChatRequestUserMessage{
				Content: azopenai.NewChatRequestUserMessageContent(msg.Content),
			}
		case "assistant":
			chatMessages[i] = &azopenai.ChatRequestAssistantMessage{
				Content: to.Ptr(msg.Content),
			}
		default:
			return "", fmt.Errorf("unsupported message role: %s", msg.Role)
		}
	}

	resp, err := p.client.GetChatCompletions(ctx, azopenai.ChatCompletionsOptions{
		Messages:       chatMessages,
		MaxTokens:      to.Ptr(p.maxTokens),
		Temperature:    to.Ptr(p.temperature),
		DeploymentName: to.Ptr(p.deploymentName),
	}, nil)

	if err != nil {
		return "", fmt.Errorf("Azure OpenAI completion failed: %w", err)
	}

	if len(resp.Choices) == 0 {
		return "", fmt.Errorf("no response from Azure OpenAI")
	}

	if resp.Choices[0].Message.Content == nil {
		return "", fmt.Errorf("empty response from Azure OpenAI")
	}

	return *resp.Choices[0].Message.Content, nil
}

// StreamComplete implements streaming for Azure OpenAI
func (p *AzureOpenAIProvider) StreamComplete(ctx context.Context, messages []Message, onChunk func(string) error) error {
	chatMessages := make([]azopenai.ChatRequestMessageClassification, len(messages))
	
	for i, msg := range messages {
		switch msg.Role {
		case "system":
			chatMessages[i] = &azopenai.ChatRequestSystemMessage{
				Content: to.Ptr(msg.Content),
			}
		case "user":
			chatMessages[i] = &azopenai.ChatRequestUserMessage{
				Content: azopenai.NewChatRequestUserMessageContent(msg.Content),
			}
		case "assistant":
			chatMessages[i] = &azopenai.ChatRequestAssistantMessage{
				Content: to.Ptr(msg.Content),
			}
		}
	}

	stream, err := p.client.GetChatCompletionsStream(ctx, azopenai.ChatCompletionsOptions{
		Messages:       chatMessages,
		MaxTokens:      to.Ptr(p.maxTokens),
		Temperature:    to.Ptr(p.temperature),
		DeploymentName: to.Ptr(p.deploymentName),
	}, nil)

	if err != nil {
		return fmt.Errorf("failed to start Azure OpenAI stream: %w", err)
	}
	defer stream.Close()

	for {
		resp, err := stream.Read()
		if err != nil {
			if err == context.Canceled {
				return nil
			}
			return fmt.Errorf("error reading stream: %w", err)
		}

		if len(resp.Choices) > 0 && resp.Choices[0].Delta.Content != nil {
			if err := onChunk(*resp.Choices[0].Delta.Content); err != nil {
				return err
			}
		}

		if resp.Choices[0].FinishReason != nil {
			break
		}
	}

	return nil
}

// SetTemperature sets the temperature for completions
func (p *AzureOpenAIProvider) SetTemperature(temp float32) {
	p.temperature = temp
}

// SetMaxTokens sets the max tokens for completions
func (p *AzureOpenAIProvider) SetMaxTokens(tokens int32) {
	p.maxTokens = tokens
}