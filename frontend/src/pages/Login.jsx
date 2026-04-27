import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { LogIn, User, Lock, AlertCircle, Loader2 } from 'lucide-react';

const TEXT = {
  title: 'تسجيل الدخول',
  username: 'اسم المستخدم',
  password: 'كلمة المرور',
  submit: 'دخول إلى النظام',
  error: 'خطأ في بيانات الدخول',
  loading: 'جاري التحقق...'
};

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const success = await login(username, password);
      if (success) {
        navigate('/');
      } else {
        setError(TEXT.error);
      }
    } catch (err) {
      const backendError = err.response?.data?.detail || err.response?.data?.error || err.message;
      setError(backendError === 'No active account found with the given credentials' 
        ? TEXT.error 
        : `${TEXT.error} (${backendError})`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      dir="rtl"
      className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"
    >
      <div className="max-w-md w-full p-8 bg-white dark:bg-slate-800 rounded-3xl shadow-xl border border-gray-100 dark:border-slate-700 relative overflow-hidden">
        <div className="relative">
          <div className="text-center mb-10">
            <div className="mb-6">
              <img 
                src="/assets/logo_ye.png" 
                alt="Logo" 
                className="w-32 h-32 mx-auto object-contain drop-shadow-lg animate-pulse-slow"
                onError={(e) => { e.target.src = "https://via.placeholder.com/150?text=YE+LOGO"; }}
              />
            </div>
            <h2 className="text-xl font-bold text-blue-900 dark:text-white mb-4 font-cairo">
              المؤسسة الاقتصادية اليمنية<br/>
              قطاع الانتاج الزراعي والحيواني<br/>
              <span className="text-sm font-medium text-gray-500">النظام الفني الرقابي</span>
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-700 dark:text-gray-300 block">
                {TEXT.username}
              </label>
              <div className="relative group">
                <User className="absolute right-4 top-3.5 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pr-12 pl-4 py-3 bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all outline-none font-medium dark:text-white"
                  placeholder="admin"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-700 dark:text-gray-300 block">
                {TEXT.password}
              </label>
              <div className="relative group">
                <Lock className="absolute right-4 top-3.5 w-5 h-5 text-gray-400 group-focus-within:text-blue-600 transition-colors" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pr-12 pl-4 py-3 bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all outline-none font-medium dark:text-white"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                <p className="text-sm font-bold text-rose-600 dark:text-rose-400">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-xl shadow-lg shadow-blue-900/20 transform transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>{TEXT.loading}</span>
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  <span>{TEXT.submit}</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
