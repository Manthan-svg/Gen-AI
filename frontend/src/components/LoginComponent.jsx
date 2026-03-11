import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api.util';

function LoginComponent({loading }) {
  const [form, setForm] = useState({
    username: '',
    password: '',
    department: 'General',
  });

  const departments = [
    'General',
    'Engineering',
    'Finance',
    'HR',
    'Marketing',
    'Operations',
    'Sales',
    'Support',
    'SDE',
  ];

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.username || !form.password || !form.department) {
      console.log("Filled out all the fields.");
      return;
    }
    try {
      const response = await api.post("/login", form);

      if (response) {
        localStorage.setItem("user-info", JSON.stringify(response.data.user));
        // Store token as plain string for cleaner Authorization header
        localStorage.setItem("token", response.data.Token);

        window.location.href = "/app";
      }
    } catch (err) {
      alert(err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-200 flex items-center justify-center">
      <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg p-8 border">
        <h2 className="text-2xl font-bold mb-6 text-slate-800 text-center">
          Sign in to <span className="text-blue-600 font-extrabold">DEEPCONTEXT</span>
        </h2>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm mb-1 font-medium text-slate-700" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              value={form.username}
              onChange={handleChange}
              disabled={loading}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
              type="text"
              placeholder="Enter your username"
              required
            />
          </div>
          <div>
            <label className="block text-sm mb-1 font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              autoComplete="current-password"
              value={form.password}
              onChange={handleChange}
              disabled={loading}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
              type="password"
              placeholder="Enter your password"
              required
            />
          </div>
          <div>
            <label className="block text-sm mb-1 font-medium text-slate-700" htmlFor="department">
              Department
            </label>
            <select
              id="department"
              name="department"
              value={form.department}
              onChange={handleChange}
              disabled={loading}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
              required
            >
              {departments.map((dept) => (
                <option value={dept} key={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow transition disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {loading ? 'Logging in...' : 'Log in'}
          </button>
        </form>
        <p className="mt-4 text-xs text-center text-slate-500">
          Don&apos;t have an account?{' '}
          <Link to="/signup" className="text-blue-600 font-semibold hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

export default LoginComponent;