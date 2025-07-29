// firestore-import/deleteAllQuestions.js

const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const serviceAccount = require("./serviceAccount.json");

// ✅ Initialize Firebase
initializeApp({
  credential: cert(serviceAccount),
});

const db = getFirestore();

async function deleteAllQuestions() {
  const snapshot = await db.collection("triviaQuestions").get();
  const batch = db.batch();

  snapshot.docs.forEach((doc) => {
    batch.delete(doc.ref);
  });

  await batch.commit();
  console.log(`✅ Deleted ${snapshot.size} question(s) from Firestore.`);
}

deleteAllQuestions().catch((err) => {
  console.error("❌ Failed to delete questions:", err);
});
