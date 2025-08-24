// frontend/src/components/Chat.jsx
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios'

export default function Chat(){
  const [q, setQ] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const streamRef = useRef('')

  const send = async ()=> {
    if(!q) return
    setMessages(m=>[...m,{from:'user', text:q}])
    setLoading(true)
    streamRef.current = ''
    try {
      const resp = await fetch('/api/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({query: q})
      })
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let done = false
      while(!done){
        const {value, done: readerDone} = await reader.read()
        done = readerDone
        if(value){
          const text = decoder.decode(value)
          // append streaming text
          streamRef.current += text
          // keep a temporary bot message
          setMessages(m=>{
            const others = m.filter(x=>x.from !== 'bot_temp')
            return [...others, {from:'bot_temp', text: streamRef.current}]
          })
        }
      }
      // After stream complete, final message may include footer JSON; try to parse last line
      const all = streamRef.current
      // try to find last JSON footer
      const lastBrace = all.lastIndexOf('{')
      let finalText = all
      let footer = null
      if(lastBrace != -1){
        try {
          footer = JSON.parse(all.substring(lastBrace))
          finalText = all.substring(0, lastBrace)
        } catch(e){}
      }
      // replace temp message with final bot message
      setMessages(m=>{
        const withoutTemp = m.filter(x=>x.from !== 'bot_temp')
        return [...withoutTemp, {from:'bot', text: finalText, footer: footer}]
      })
    } catch(e){
      setMessages(m=>[...m,{from:'bot', text: 'Error: '+ String(e)}])
    } finally {
      setLoading(false)
      setQ('')
    }
  }

  return (
    <div className="chat-container">
      <h2 style={{ textAlign: 'center', color: '#444' }}>RAG Chat System</h2>
      <div className="chat-messages" ref={el => el && (el.scrollTop = el.scrollHeight)}>
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.from.startsWith('bot') ? 'bot' : 'user'}`}>
            <b>{m.from === 'user' ? 'You' : 'Bot'}:</b>
            <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
            {m.footer && (
              <pre className="message-footer">
                {JSON.stringify(m.footer, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
      <div className="chat-input-area">
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && send()}
          placeholder="Ask a question about the crawled content..."
        />
        <button onClick={send} disabled={loading}>
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
