// firestore-import/import.js
const { readFileSync } = require("fs");
const path = require("path");
const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore, Timestamp } = require("firebase-admin/firestore");
const serviceAccount = require("./serviceAccount.json");

// ✅ Initialize Firebase with service account
initializeApp({
  credential: cert(serviceAccount),
});

const db = getFirestore();

async function importQuestions() {
  try {
    // ✅ Use path.join to safely reference file with space in folder name
    const filePath = path.join(__dirname, "../Questions-Data/International/World Cup/world-cup-hard-50.json");
    const data = readFileSync(filePath, "utf-8");
    const questions = JSON.parse(data);

    const batch = db.batch();
    const collectionRef = db.collection("questions");

    questions.forEach((q) => {
      const docRef = collectionRef.doc(); // Auto-ID, or use q.question if you want to avoid duplicates

      batch.set(docRef, {
        question: q.question,
        answer: q.answer,
        options: q.options,
        category: q.category || "",
        subcategories: q.subcategories || [],
        difficulty: q.difficulty || "default",
        source: q.source || "",
        createdAt: Timestamp.now(),
        updatedAt: Timestamp.now()
      });
    });

    await batch.commit();
    console.log(`✅ Successfully imported ${questions.length} questions to Firestore.`);
  } catch (error) {
    console.error("❌ Failed to import questions:", error);
  }
}

importQuestions();
