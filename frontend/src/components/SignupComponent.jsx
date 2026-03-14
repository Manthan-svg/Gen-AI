import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api.util';

function SignupComponent({ loading }) {
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
    'Workstation',
  ];

  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.username || !form.password || !form.department) {
      console.log('Please fill out all the fields.');
      return;
    }

    try {
      setSubmitting(true);
      const response = await api.post('/signup', form);

      if (response && response.data) {
        const user = response.data.user;
        const token = response.data['Access-Token'];

        if (user && token) {
          localStorage.setItem('user-info', JSON.stringify(user));
          localStorage.setItem('token', token);

          window.location.href = '/app';
        }
      }
    } catch (err) {
      alert(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-200 flex items-center justify-center">
      <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg p-8 border">
        <h2 className="text-2xl font-bold mb-2 text-slate-800 text-center">
          Create your <span className="text-blue-600 font-extrabold">DEEPCONTEXT</span> account
        </h2>
        <p className="text-xs text-slate-500 text-center mb-6">
          Sign up to start secure contextual conversations.
        </p>
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
              disabled={loading || submitting}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
              type="text"
              placeholder="Choose a username"
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
              autoComplete="new-password"
              value={form.password}
              onChange={handleChange}
              disabled={loading || submitting}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
              type="password"
              placeholder="Create a password"
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
              disabled={loading || submitting}
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
            disabled={loading || submitting}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow transition disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {submitting ? 'Signing up...' : 'Sign up'}
          </button>
        </form>

        <p className="mt-4 text-xs text-center text-slate-500">
          Already have an account?{' '}
          <Link to="/" className="text-blue-600 font-semibold hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default SignupComponent;

