import React from 'react';

const PrivacyPolicy = () => {
  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-4">Privacy Policy</h1>
      <p className="mb-4">
        At QuizLazo, we respect your privacy. This Privacy Policy outlines how we collect, use, and protect information when you use our website.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Information Collection</h2>
      <p className="mb-4">
        We do not require users to create accounts or submit personal information. However, we may collect non-personal data such as IP addresses, device type, and browser version to improve the site and analyze usage.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Cookies and Ads</h2>
      <p className="mb-4">
        This site may use cookies to enhance functionality and support Google AdSense advertising. Google and its partners may use cookies to personalize ads and measure performance.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Third-Party Services</h2>
      <p className="mb-4">
        We may use third-party tools (such as analytics or advertising services) that collect information per their own privacy policies. We encourage you to review those policies for details.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Your Consent</h2>
      <p className="mb-4">
        By using QuizLazo, you consent to the terms in this Privacy Policy.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Contact Us</h2>
      <p>
        If you have questions about this policy, please contact us at{' '}
        <a href="mailto:privacy@quizlazo.com" className="text-blue-400 underline">
          privacy@quizlazo.com
        </a>.
      </p>
    </div>
  );
};

export default PrivacyPolicy;
