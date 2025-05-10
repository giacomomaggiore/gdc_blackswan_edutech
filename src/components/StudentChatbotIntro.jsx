import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

function StudentChatbotIntro({ onComplete }) {
  const [introData, setIntroData] = useState(null);
  const [answers, setAnswers] = useState(['', '']);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch questions from backend
    fetch('http://localhost:5000/api/intro')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to fetch questions');
        }
        return response.json();
      })
      .then(data => {
        setIntroData(data);
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching intro data:', error);
        setError('Failed to load questions. Please make sure the backend server is running.');
        setIsLoading(false);
      });
  }, []);

  const handleAnswerChange = (index, value) => {
    const newAnswers = [...answers];
    newAnswers[index] = value;
    setAnswers(newAnswers);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (currentQuestion < introData.questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    } else {
      try {
        setIsLoading(true);
        const response = await fetch('http://localhost:5000/api/generate-story', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            interests: answers.join(', ') // Combine both answers as interests
          }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.error || 'Failed to generate story');
        }
        
        if (!data.sceneText || !data.question || !data.options) {
          throw new Error('Invalid story data received from server');
        }
        
        onComplete({ answers, storyData: data });
      } catch (error) {
        console.error('Error generating story:', error);
        setError(error.message || 'Failed to generate story. Please try again.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto bg-red-500/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
        <h2 className="text-2xl font-bold mb-6 text-center text-red-500">Error</h2>
        <p className="text-center">{error}</p>
        <p className="text-center mt-4">Make sure the backend server is running at http://localhost:5000</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl"
    >
      <h2 className="text-2xl font-bold mb-6 text-center">Welcome to Math Adventures!</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <label className="block text-lg">
            {introData.questions[currentQuestion]}
          </label>
          <textarea
            value={answers[currentQuestion]}
            onChange={(e) => handleAnswerChange(currentQuestion, e.target.value)}
            className="w-full p-4 rounded-lg bg-white/5 border border-white/20 focus:border-white/40 focus:outline-none"
            rows="4"
            placeholder="Tell us about yourself..."
            required
          />
        </div>
        <button
          type="submit"
          className="w-full py-3 px-6 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-semibold transition-colors"
        >
          {currentQuestion < introData.questions.length - 1 ? 'Next Question' : 'Start Adventure'}
        </button>
      </form>
    </motion.div>
  );
}

export default StudentChatbotIntro; 