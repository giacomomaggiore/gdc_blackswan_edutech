import { useState } from 'react';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState("");
  const [username, setUsername] = useState("");
  const [context, setContext] = useState("");
  const [correct, setCorrect] = useState("");
  const [story, setStory] = useState("");
  const [fullStory, setFullStory] = useState("");
  

  const startQuiz = async () => {
    const res = await fetch("http://127.0.0.1:8000/start", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username: username,           // supponendo tu abbia uno useState(username)
        session_id: sessionId,
        context: context  
      })
    });
  
    const data = await res.json();
  
    setSessionId(data.session_id);
    setContext(data.context);
    setQuestion(data.question);
    setFullStory(data.full_story);
    setStory(data.story); // se lo ricevi
    setAnswers(data.answers);   // se le ricevi
    setCorrect(data.correct);   // se lo ricevi
    setResult("");
  };

  const sendAnswer = async (answer) => {
    const res = await fetch("http://127.0.0.1:8000/continue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        user_answer: answer,
        username: username,
        context: context,
      }),
    });
  
    const data = await res.json();
  
    //  aggiorniamo tutto con la nuova domanda generata
    setResult(data.result);
    setQuestion(data.question);
    setAnswers(data.answers);
    setStory(data.story);
    setCorrect(data.correct);
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    startQuiz(); // avvia il quiz dopo aver ricevuto il nome
  };

  return (
    <div style={{ padding: 20 }}>
      {!sessionId && !story && (<h1>Math Quest</h1>)}

      {!sessionId && !story && (
        <form onSubmit={handleFormSubmit}>
          <label>
            Name:
            <input
              type="text"
              value={username}
              onChange={(f) => setUsername(f.target.value)}
              required
            />
          </label>
          <label>
            Context:
            <input
              type="text"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              required
            />
          </label>

          <button type="submit">Inizia Quiz</button>
        </form>
      )}
      
      { story &&     
      <p>{story}</p>}
      {question && 
      
      
      <p><strong>{question}</strong> </p>}

      {question && (
        <div>
          <button onClick={() => sendAnswer("a")}>{answers["a"]}</button>
          <button onClick={() => sendAnswer("b")}>{answers["b"]}</button>
          <button onClick={() => sendAnswer("c")}>{answers["c"]}</button>


        </div>
      )}

      {result && !story && <h4>Risultato: {result}</h4>}
    </div>
  );
}

export default App;