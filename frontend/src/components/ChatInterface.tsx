import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, User, Bot } from 'lucide-react'
import ExplainToButton from './ExplainToButton'
import type { Message } from '../types'

interface ChatInterfaceProps {
  messages: Message[]
  isLoading: boolean
  onSendMessage: (message: string) => void
  suggestions: string[]
  onSuggestionClick: (suggestion: string) => void
  initialInput?: string
}

export default function ChatInterface({
  messages,
  isLoading,
  onSendMessage,
  suggestions,
  onSuggestionClick,
  initialInput,
}: ChatInterfaceProps) {
  const [input, setInput] = useState(initialInput || '')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (initialInput) {
      setInput(initialInput)
    }
  }, [initialInput])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim())
      setInput('')
    }
  }

  return (
    <div className="bg-card rounded-xl border border-border flex flex-col h-[600px]">
      {/* Chat Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h2 className="font-semibold text-foreground">Security Intelligence Chat</h2>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Ask about threats, vulnerabilities, and security trends
        </p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
              <Bot className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">
              Welcome to Security Intelligence
            </h3>
            <p className="text-muted-foreground text-sm max-w-sm mx-auto">
              I can help you understand security threats, track story evolution,
              and predict future risks. Try one of the suggestions below.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {isLoading && (
          <div className="flex gap-3 animate-message">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 animate-glow-pulse">
              <Bot className="w-4 h-4 text-primary-foreground" />
            </div>
            <div className="bg-muted rounded-2xl rounded-tl-none px-4 py-3">
              <p className="text-sm text-muted-foreground mb-2">Analyzing threats...</p>
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {suggestions.length > 0 && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={suggestion}
                onClick={() => onSuggestionClick(suggestion)}
                className="text-sm px-3 py-1.5 bg-muted hover:bg-accent text-muted-foreground hover:text-accent-foreground rounded-full transition-all hover:scale-105 animate-pill"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about security threats..."
            disabled={isLoading}
            className="flex-1 bg-muted border border-border rounded-lg px-4 py-3 text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-3 bg-primary hover:bg-primary/90 disabled:bg-muted disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            <Send className="w-5 h-5 text-primary-foreground" />
          </button>
        </div>
      </form>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 animate-message ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-muted' : 'bg-primary'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-foreground" />
        ) : (
          <Bot className="w-4 h-4 text-primary-foreground" />
        )}
      </div>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-none'
            : 'bg-muted text-foreground rounded-tl-none'
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        {message.data?.articles && message.data.articles.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs text-muted-foreground mb-2">Related Articles:</p>
            <div className="space-y-1">
              {message.data.articles.slice(0, 3).map((article) => (
                <a
                  key={article.id}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-primary hover:text-primary/80 truncate"
                >
                  {article.title}
                </a>
              ))}
            </div>
          </div>
        )}
        {/* Explain It To... Button for assistant messages with content */}
        {!isUser && message.content && (
          <div className="mt-3 pt-3 border-t border-border">
            <ExplainToButton
              content={message.content}
              articleId={message.data?.articles?.[0]?.id}
            />
          </div>
        )}
      </div>
    </div>
  )
}
