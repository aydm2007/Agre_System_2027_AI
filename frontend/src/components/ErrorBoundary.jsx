import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(_error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Uncaught error:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8 text-center border border-gray-100">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
              <AlertTriangle className="w-8 h-8 text-red-600" />
            </div>

            <h1 className="text-2xl font-bold text-gray-900 mb-2">عذراً، حدث خطأ غير متوقع</h1>

            <p className="text-gray-600 mb-8">
              نأسف لهذا الإزعاج. حاول تحديث الصفحة، أو تواصل مع الدعم الفني إذا استمرت المشكلة.
            </p>

            <div className="space-y-3">
              <button
                onClick={this.handleReload}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors shadow-sm active:scale-95 duration-200"
              >
                <RefreshCw className="w-4 h-4" />
                تحديث الصفحة
              </button>

              <button
                onClick={() => this.setState({ hasError: false })}
                className="w-full px-4 py-3 text-gray-600 hover:bg-gray-50 rounded-lg font-medium transition-colors"
              >
                المحاولة مرة أخرى
              </button>
            </div>

            {import.meta.env.DEV && this.state.error && (
              <div className="mt-8 text-left bg-gray-900 rounded-lg p-4 overflow-auto max-h-64 text-xs font-mono text-red-300">
                <p className="font-bold mb-2 text-white">{this.state.error.toString()}</p>
                <pre>{this.state.errorInfo.componentStack}</pre>
              </div>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
