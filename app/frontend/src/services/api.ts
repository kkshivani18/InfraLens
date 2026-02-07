const BASE_URL = "http://127.0.0.1:8000/api";

export const chatService = {
  async sendMessage(message: string) {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    return response.json();
  }
};

export const repoService = {
  async ingestRepo(repoUrl: string) {
    const response = await fetch(`${BASE_URL}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl }),
    });
    return response.json();
  },
  
  async deleteRepo(repoId: string) {
    console.log(`Deleting repo: ${repoId}`);
  }
};