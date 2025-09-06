# 🤝 Contributing to Meetscribe

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/your-username/meetscribe.git`
3. **Create** a feature branch: `git checkout -b feature/amazing-feature`
4. **Set up** development environment (see [DEVELOPER.md](DEVELOPER.md))
5. **Make** your changes
6. **Test** your changes: `python -m pytest`
7. **Commit** your changes: `git commit -m 'Add amazing feature'`
8. **Push** to your branch: `git push origin feature/amazing-feature`
9. **Create** a Pull Request

## 🐛 Reporting Issues

- Use the provided [issue templates](.github/ISSUE_TEMPLATE/)
- Include detailed steps to reproduce
- Provide environment information
- Attach relevant logs or screenshots

## 💡 Feature Requests

- Check existing issues first
- Use the feature request template
- Be specific about the problem and solution
- Consider backward compatibility

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use type hints where possible
- Write descriptive variable/function names
- Keep functions focused and single-purpose
- Add docstrings for public functions

### Testing
- Write tests for new features
- Ensure all tests pass: `python -m pytest`
- Aim for high test coverage
- Test edge cases and error conditions

### Documentation
- Update documentation for new features
- Keep README.md current
- Add code comments for complex logic
- Update examples and tutorials

## 📝 Adding New Features

1. Create new modules in `app/` directory
2. Implement functionality following the existing patterns
3. Add CLI commands in `app/cli.py` using Typer
4. Add tests in `tests/test_your_feature.py`
5. Update documentation
6. Test the new feature: `python -m app.cli --help`

## 🔧 Build System Changes

- Test builds on all supported platforms
- Update build configurations for new dependencies
- Verify executable functionality
- Update build documentation

## 📋 Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Keep commits focused on single changes
- Squash related commits before merging

### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

**Examples:**
```
feat(screenshot): add clipboard integration
fix(config): handle missing config files gracefully
docs(readme): update installation instructions
```

## 🎯 Pull Request Process

1. **Update** the README.md if needed
2. **Update** the documentation
3. **Add** tests for new functionality
4. **Ensure** CI passes
5. **Request** review from maintainers
6. **Address** review feedback
7. **Merge** when approved

## 🏗️ Architecture Guidelines

### Action Design
- Actions should be stateless when possible
- Use configuration for customization
- Return meaningful result messages
- Handle errors gracefully
- Keep dependencies minimal

### CLI Design
- Follow consistent command structure
- Use clear help text
- Provide useful error messages
- Support both interactive and automated use

### Configuration
- Use TOML for human-readable config
- Support environment variable overrides
- Validate configuration on startup
- Provide sensible defaults

## 🧪 Testing Strategy

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Test error conditions
- Verify edge cases

### Integration Tests
- Test action execution
- Verify CLI commands
- Test configuration loading
- Validate build outputs

### End-to-End Tests
- Test complete workflows
- Verify executable functionality
- Test cross-platform compatibility

## 📊 Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes without discussion
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Error handling appropriate

## 🎉 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Acknowledged in documentation
- Invited to join the maintainer team (for significant contributions)

## 📞 Getting Help

- **Issues:** Use GitHub issues for bugs and features
- **Discussions:** Use GitHub discussions for questions
- **Documentation:** Check [docs/](docs/) first
- **Community:** Join our Discord/Slack (when available)

## 📜 License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

Thank you for contributing to Meetscribe! 🚀
