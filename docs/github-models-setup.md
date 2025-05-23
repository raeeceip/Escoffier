# GitHub Models Setup Guide

This guide explains how to set up and use GitHub Models for free testing with Escoffier-Bench.

## Prerequisites

1. A GitHub account
2. A GitHub personal access token with appropriate permissions

## Getting Started

### 1. Create a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" (classic)
3. Give it a descriptive name like "Escoffier-Bench Testing"
4. Select the following scopes:
   - `repo` (for accessing GitHub Models)
   - `read:org` (if using organization account)
5. Click "Generate token" and copy it immediately

### 2. Set Environment Variable

```bash
export GITHUB_TOKEN="your-github-token-here"
```

Or add it to your `.env` file:
```
GITHUB_TOKEN=your-github-token-here
```

### 3. Configure Escoffier-Bench

Update your `configs/config.yaml` to include GitHub Models:

```yaml
providers:
  - type: github_models
    enabled: true
    models:
      - gpt-4o-mini
      - gpt-4o
      - Meta-Llama-3.1-70B-Instruct
      - Mistral-large-2407
```

## Available Models

GitHub Models provides free access to these models:

| Model ID | Description | Max Tokens | Best For |
|----------|-------------|------------|----------|
| `gpt-4o-mini` | GPT-4 Optimized Mini | 128,000 | General tasks, fast responses |
| `gpt-4o` | GPT-4 Optimized | 128,000 | Complex reasoning |
| `Phi-3.5-mini-instruct` | Microsoft Phi 3.5 | 8,192 | Lightweight tasks |
| `Meta-Llama-3.1-70B-Instruct` | Llama 3.1 70B | 8,192 | Open-source alternative |
| `Meta-Llama-3.1-405B-Instruct` | Llama 3.1 405B | 8,192 | High-quality responses |
| `Mistral-large-2407` | Mistral Large | 32,000 | European multilingual |
| `AI21-Jamba-1.5-Large` | Jamba 1.5 | 8,192 | Creative writing |

## Rate Limits

GitHub Models free tier includes:
- 15 requests per minute
- 40,000 tokens per minute
- No daily limits

## Usage Example

### CLI Usage

```bash
# Start the system with GitHub Models
./start-all.sh

# Use the CLI to test
./cli/cli
```

### API Usage

```bash
# Test with curl
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "github_models",
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

### Playground Usage

1. Start the playground: `./start-all.sh`
2. Navigate to http://localhost:8090
3. Select "GitHub Models" from the provider dropdown
4. Choose a model and start testing

## Troubleshooting

### Authentication Failed
- Ensure your GitHub token is valid and has the correct permissions
- Check that the token is properly set in your environment

### Rate Limit Exceeded
- GitHub Models has a 15 requests/minute limit
- Implement retry logic with exponential backoff
- Consider using multiple tokens for higher throughput

### Model Not Available
- Some models may be region-restricted
- Check GitHub's model availability page
- Try a different model from the supported list

## Cost

GitHub Models is **completely free** for personal use, making it ideal for:
- Development and testing
- Prototyping
- Educational purposes
- Small-scale applications

## Integration with Escoffier-Bench

The GitHub Models provider is automatically registered when you set the `GITHUB_TOKEN` environment variable. You can use it in:

1. **Agent Testing**: Test different agent behaviors with various models
2. **Evaluation**: Compare model performance across providers
3. **Development**: Build and test without API costs

## Security Best Practices

1. Never commit your GitHub token to version control
2. Use environment variables or secure secret management
3. Rotate tokens regularly
4. Use separate tokens for different environments

## Further Resources

- [GitHub Models Documentation](https://docs.github.com/en/github-models)
- [Model Marketplace](https://github.com/marketplace/models)
- [API Reference](https://docs.github.com/en/rest/models)