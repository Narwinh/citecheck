// Bundled so the landing page works while the backend sleeps.
// Mirrors backend/app/examples.json (served at /api/examples).
export const EXAMPLES = [
  { question: "How does LangGraph handle cycles compared to LangChain chains?", category: "technical" },
  { question: "What did the 2024 Nobel Prize in Physics recognize, and who won it?", category: "factual" },
  {
    question: "Who directed the film that won Best Picture in 2020, and what country is the director from?",
    category: "multi-hop",
  },
  { question: "What causes the northern lights?", category: "science" },
  { question: "What is the latest stable version of Python, and what are its headline features?", category: "recent" },
  { question: "In what year did Albert Einstein win his second Nobel Prize?", category: "trick question" },
];
