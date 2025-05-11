import { useState } from 'react';
import './index.css';

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
        username: username,
        session_id: sessionId,
        context: context
      })
    });

    const data = await res.json();

    setSessionId(data.session_id);
    setContext(data.context);
    setQuestion(data.question);
    setFullStory(data.full_story);
    setStory(data.story);
    setAnswers(data.answers);
    setCorrect(data.correct);
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

    setResult(data.result);
    setQuestion(data.question);
    setAnswers(data.answers);
    setStory(data.story);
    setCorrect(data.correct);
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    startQuiz();
  };

  return (
    <div className="min-h-screen bg-[url(/Users/giacomomaggiore/Desktop/CODING/gdc_blackswan_edutech/my-quiz-app/src/assets/bg.png)] bg-w-full bg-cover flex items-center justify-center" 
    >
      <div className=" bg-white/70 backdrop-blur-sm  absolute inset-0 max-h-fit flex flex-row justify-around
" >
    <div className='ml-10 m4-10'>
    <button className=" text-black rounded-lg py-3 hover:font-bold transition duration-200 transform hover:scale-105" >
                MISSION
              </button>
</div>
<div className='ml-10 m4-10'>
    <button className=" text-black rounded-lg py-3 hover:font-bold transition duration-200 transform hover:scale-105" >
                TEACHER DASHBOARD
              </button>
</div>
<div className='ml-10 m4-10'>
    <button className=" text-black rounded-lg py-3 hover:font-bold transition duration-200 transform hover:scale-105" >
                ABOUT US
              </button>
</div>

      </div>
 <div className="w-full max-w-3xl bg-white/70 backdrop-blur-sm rounded-none md:rounded-2xl shadow-xl p-6 md:p-8 flex flex-col">

        {!sessionId && !story ? (
          <div className="space-y-6">
            <div className="text-center">
              <h1 className="text-6xl md:text-6xl font-extrabold text-indigo-900 mb-2">Math Quest</h1>
              <p className="text-black">Begin your mathematical adventure</p>
            </div>
            
            <form onSubmit={handleFormSubmit} className="space-y-5">
              <div className="space-y-1">
                <label className="block text-gray-700 font-medium">
                  Your Hero's Name 🦸🏻‍♂️
                </label>
                <input 
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full rounded-lg bg-white border border-gray-300 px-4 py-2.5 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                  placeholder="Enter your hero name"
                />
              </div>
              
              <div className="space-y-1">
                <label className="block text-gray-700 font-medium">
                  Your Fantasy World 🌎
                </label>
                <input
                  type="text"
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  required
                  className="w-full rounded-lg bg-white border border-gray-300 px-4 py-2.5 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                  placeholder="Be creative!"
                />
              </div>
              
              <button 
                type="submit" 
                className="w-full bg-indigo-600 text-white rounded-lg py-3 font-semibold hover:bg-indigo-700 transition duration-200 transform hover:scale-105"
              >
                Start the Adventure
              </button>
            </form>
          </div>
        ) : (
          <div className="h-full flex flex-col ">
            {/* Game Content */}
            <div className=" flex-grow overflow-y-auto max-h-[70vh] md:max-h-[60vh] scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 pr-2">
              {story && (
                <div className="b-solid border-1 bg-trasparent-50  bg-opacity-10 rounded-xl p-4 mb-6 border-white shadow-sm">
                  <p className="text-gray-700 text-base md:text-lg">{story}</p>
                </div>
              )}
            </div>
            
            {/* Question and Answers */}
            <div className="mt-auto">
              {question && (
                <div className="mb-4">
                  <p className="font-semibold text-gray-900 text-lg md:text-xl text-center mb-4 px-2 py-1 bg-yellow-50 rounded-lg">
                    {question}
                  </p>
                  
                  <div className="space-y-3">
                    {Object.keys(answers).map((key) => (
                      <button
                        key={key}
                        onClick={() => sendAnswer(key)}
                        className="w-full bg-white hover:bg-indigo-50 text-gray-800 rounded-xl py-3 px-4 font-medium transition border border-gray-200 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-left flex items-center"
                      >
                        <span className="h-8 w-8 rounded-full bg-indigo-100 text-indigo-800 flex items-center justify-center font-bold mr-3">
                          {key.toUpperCase()}
                        </span>
                        <span>{answers[key]}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              
              {result && !story && (
                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-xl">
                  <h4 className="text-green-700 font-semibold text-center">Risultato: {result}</h4>
                </div>
              )}
              
              {/* Restart button */}
              {sessionId && (
                <button
                  onClick={() => {
                    setSessionId(null);
                    setStory("");
                    setQuestion("");
                    setAnswers({});
                  }}
                  className="mt-6 w-full bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg py-2 font-medium transition"
                >
                  Start New Adventure
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;