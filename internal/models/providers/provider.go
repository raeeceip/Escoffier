package providers

import "context"

// Message represents a chat message
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Provider interface for LLM providers
type Provider interface {
	Complete(ctx context.Context, messages []Message) (string, error)
	StreamComplete(ctx context.Context, messages []Message, onChunk func(string) error) error
	SetTemperature(temp float32)
	SetMaxTokens(tokens int32)
}