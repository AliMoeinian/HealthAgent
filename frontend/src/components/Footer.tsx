import React from 'react';

const Footer: React.FC = () => {
  // گرفتن سال جاری به صورت داینامیک برای نمایش کپی‌رایت
  const currentYear = new Date().getFullYear();

  return (
    <footer className="w-full bg-gray-100 py-5 text-center">
      <div className="text-gray-600 text-sm space-y-1">
        {/* خط اول: اطلاعات شخصی و کپی‌رایت */}
        <p>
          © {currentYear} | Created with <span className="text-red-500 mx-1">❤</span> by Ali Moeinian
        </p>
        
        {/* خط دوم: اطلاعات پروژه و دانشگاه */}
        <p>
          As part of the{' '}
          <a
            href="https://ui.ac.ir/" // می‌توانید لینک دقیق دانشکده یا پروژه را اینجا قرار دهید
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-gray-800 hover:text-green-600 transition"
          >
            RAG Branch Isfahan University
          </a>{' '}
          project.
        </p>

  
        <p className="pt-2 text-gray-500 italic">
          ⚙️ This project is under active development and new features are on the way.
        </p>
      </div>
    </footer>
  );
};

export default Footer;