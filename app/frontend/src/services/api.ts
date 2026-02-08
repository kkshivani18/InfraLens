const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

async function getAuthHeaders(token: string | null): Promise<HeadersInit> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  return headers;
}

export const chatService = {
  async sendMessage(message: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ message }),
    });
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    return response.json();
  }
};

export const repoService = {
  async ingestRepo(repoUrl: string, token: string | null) {
    const response = await fetch(`${BASE_URL}/ingest`, {
      method: "POST",
      headers: await getAuthHeaders(token),
      body: JSON.stringify({ repo_url: repoUrl }),
    });
    
    if (response.status === 401) {
      throw new Error("Unauthorized: Please sign in again");
    }
    
    return response.json();
  },
  
  async deleteRepo(repoId: string) {
    console.log(`Deleting repo: ${repoId}`);
  }
};