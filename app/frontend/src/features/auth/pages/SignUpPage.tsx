import { SignUp } from '@clerk/clerk-react';

const SignUpPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <SignUp 
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-gray-900 shadow-xl"
          }
        }}
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
      />
    </div>
  );
};

export default SignUpPage;