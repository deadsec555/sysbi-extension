import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  lastContact: string; // ISO date
  status: 'New' | 'Contacted' | 'Qualified' | 'Proposal' | 'Negotiation' | 'Closed' | 'Lost';
  notes: string;
  agentId: string;
  interestScore?: number; // 0-100
  priority?: 'Hot' | 'Warm' | 'Cold';
  nextAction?: string;
}

export async function analyzeLeads(leads: Lead[]) {
  const prompt = `Analyze the following CRM leads and identify "Hot Leads" that need to be dialed tomorrow. 
  For each lead, provide an interest score (0-100), a priority (Hot, Warm, Cold), and a recommended next action.
  
  Leads:
  ${JSON.stringify(leads, null, 2)}
  `;

  const response = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            id: { type: Type.STRING },
            interestScore: { type: Type.NUMBER },
            priority: { type: Type.STRING, enum: ["Hot", "Warm", "Cold"] },
            nextAction: { type: Type.STRING }
          },
          required: ["id", "interestScore", "priority", "nextAction"]
        }
      }
    }
  });

  try {
    return JSON.parse(response.text);
  } catch (e) {
    console.error("Failed to parse AI response", e);
    return [];
  }
}
