#!/bin/bash
# Meetscribe Release Script
# Safely creates a new release with GitHub Actions automated builds

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REQUIRED_TOOLS=("git" "python3" "pip3")
DRY_RUN=false
SKIP_CONFIRMATIONS=false

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${PURPLE}🚀 $1${NC}"
}

# Function to ask for confirmation
confirm() {
    local message="$1"
    local default="${2:-n}"

    if [ "$SKIP_CONFIRMATIONS" = true ]; then
        return 0
    fi

    local prompt
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    echo -e "${YELLOW}$message $prompt${NC}"
    read -r response

    # Trim whitespace and convert to lowercase for comparison
    response=$(echo "$response" | tr '[:upper:]' '[:lower:]' | xargs)

    if [ "$default" = "y" ]; then
        [ -z "$response" ] || [ "$response" = "y" ] || [ "$response" = "yes" ]
    else
        [ "$response" = "y" ] || [ "$response" = "yes" ]
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate semantic version
validate_version() {
    local version="$1"
    if [[ ! "$version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$ ]]; then
        print_error "Invalid version format: $version"
        print_info "Version must follow semantic versioning (e.g., 1.0.0, v1.0.0, 1.0.0-beta.1)"
        return 1
    fi
    return 0
}

# Function to check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        print_error "Not in a git repository"
        return 1
    fi

    # Check if we're in the project root
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found. Run this script from the project root."
        return 1
    fi

    # Check required tools
    for tool in "${REQUIRED_TOOLS[@]}"; do
        if ! command_exists "$tool"; then
            print_error "Required tool not found: $tool"
            return 1
        fi
    done

    # Check if git is clean
    if [ -n "$(git status --porcelain)" ]; then
        print_error "Working directory is not clean. Please commit or stash changes first."
        git status --short
        return 1
    fi

    # Check if we're on main branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ]; then
        print_error "Not on main branch. Current branch: $current_branch"
        print_info "Please switch to main branch before releasing."
        return 1
    fi

    # Check if remote origin exists
    if ! git remote get-url origin >/dev/null 2>&1; then
        print_error "No remote origin found."
        return 1
    fi

    # Check project setup
    print_info "Validating project setup..."
    if ! python3 scripts/validate_setup.py >/dev/null 2>&1; then
        print_error "Project validation failed. Please resolve setup issues first."
        return 1
    fi

    print_success "Prerequisites check passed"
    return 0
}

# Function to get current version from pyproject.toml
get_current_version() {
    if [ ! -f "pyproject.toml" ]; then
        echo "unknown"
        return 1
    fi

    grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' || echo "unknown"
}

# Function to suggest next version
suggest_next_version() {
    local current_version="$1"
    local version_type="${2:-patch}"

    if [ "$current_version" = "unknown" ]; then
        echo "1.0.0"
        return 0
    fi

    # Remove 'v' prefix if present
    local clean_version="${current_version#v}"

    # Parse version components
    IFS='.' read -ra VERSION_PARTS <<< "$clean_version"
    local major="${VERSION_PARTS[0]}"
    local minor="${VERSION_PARTS[1]}"
    local patch="${VERSION_PARTS[2]}"

    # Remove any pre-release or build metadata
    patch=$(echo "$patch" | sed 's/[-+].*//')

    case "$version_type" in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "$major.$((minor + 1)).0"
            ;;
        patch)
            echo "$major.$minor.$((patch + 1))"
            ;;
        *)
            echo "$major.$minor.$((patch + 1))"
            ;;
    esac
}

# Function to prompt for version type
prompt_version_type() {
    echo -e "${CYAN}What type of release is this?${NC}"
    echo "1) Patch (bug fixes) - 1.0.0 → 1.0.1"
    echo "2) Minor (new features) - 1.0.0 → 1.1.0"
    echo "3) Major (breaking changes) - 1.0.0 → 2.0.0"
    echo
    echo -n "Choose [1-3] (default: 1): "
    read -r choice

    case "$choice" in
        1|"")
            echo "patch"
            ;;
        2)
            echo "minor"
            ;;
        3)
            echo "major"
            ;;
        *)
            print_warning "Invalid choice, defaulting to patch"
            echo "patch"
            ;;
    esac
}

# Function to update version in pyproject.toml
update_version() {
    local new_version="$1"

    print_step "Updating version in pyproject.toml to $new_version"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would update version to $new_version"
        return 0
    fi

    # Remove 'v' prefix if present for pyproject.toml
    local clean_version="${new_version#v}"

    # Update version in pyproject.toml
    sed -i.bak "s/^version = .*/version = \"$clean_version\"/" pyproject.toml

    if [ $? -eq 0 ]; then
        print_success "Version updated successfully"
        # Clean up backup file
        rm pyproject.toml.bak
    else
        print_error "Failed to update version"
        # Restore backup
        mv pyproject.toml.bak pyproject.toml
        return 1
    fi
}

# Function to commit changes
commit_changes() {
    local version="$1"

    print_step "Committing version change"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would commit changes for version $version"
        return 0
    fi

    git add pyproject.toml
    git commit -m "Release $version"

    if [ $? -eq 0 ]; then
        print_success "Changes committed successfully"
    else
        print_error "Failed to commit changes"
        return 1
    fi
}

# Function to push to main
push_main() {
    print_step "Pushing to main branch"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would push to main branch"
        return 0
    fi

    git push origin main

    if [ $? -eq 0 ]; then
        print_success "Pushed to main branch successfully"
    else
        print_error "Failed to push to main branch"
        return 1
    fi
}

# Function to create and push tag
create_tag() {
    local version="$1"

    print_step "Creating and pushing tag $version"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN: Would create and push tag $version"
        return 0
    fi

    # Create annotated tag
    git tag -a "$version" -m "Release $version"

    if [ $? -eq 0 ]; then
        print_success "Tag created successfully"
    else
        print_error "Failed to create tag"
        return 1
    fi

    # Push tag
    git push origin "$version"

    if [ $? -eq 0 ]; then
        print_success "Tag pushed successfully"
    else
        print_error "Failed to push tag"
        return 1
    fi
}

# Function to show next steps
show_next_steps() {
    local version="$1"
    local repo_url=$(git remote get-url origin | sed 's/\.git$//' | sed 's/git@github\.com:/https:\/\/github.com\//')

    print_header "🎉 Release $version Created Successfully!"
    echo
    print_info "Next steps:"
    echo
    print_info "1. Monitor GitHub Actions:"
    echo "   🌐 $repo_url/actions"
    echo
    print_info "2. Check the release:"
    echo "   🌐 $repo_url/releases"
    echo
    print_info "3. Download binaries:"
    echo "   • Linux: meetscribe-linux.tar.gz"
    echo "   • macOS: meetscribe-macos.tar.gz"
    echo "   • Windows: meetscribe-windows.zip"
    echo
    print_info "4. Test the executables:"
    echo "   ./meetscribe --help"
    echo
    print_warning "Note: It may take a few minutes for GitHub Actions to start building"
}

# Function to show usage
show_usage() {
    cat << EOF
Meetscribe Release Script

USAGE:
    $0 [version] [options]

ARGUMENTS:
    version    Release version (e.g., 1.0.0, v1.0.0)
               If not provided, will suggest the next version

OPTIONS:
    --dry-run              Show what would be done without making changes
    --yes, -y              Skip confirmation prompts
    --help, -h             Show this help message

EXAMPLES:
    $0                      # Auto-suggest next version
    $0 1.0.0               # Create release v1.0.0
    $0 v2.1.0 --dry-run    # Dry run of v2.1.0 release
    $0 1.0.0 --yes         # Create release without confirmations

SAFETY FEATURES:
    • Validates prerequisites before starting
    • Confirms each major step
    • Creates backups of modified files
    • Provides clear rollback instructions on failure
    • Dry-run mode for testing
    • Auto-suggests semantic version increments

EOF
}

# Main function
main() {
    local version=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --yes|-y)
                SKIP_CONFIRMATIONS=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [ -z "$version" ]; then
                    version="$1"
                else
                    print_error "Multiple versions specified"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Show current version
    current_version=$(get_current_version)
    print_info "Current version: $current_version"

    # If no version provided, suggest the next version
    if [ -z "$version" ]; then
        # Ask for version type
        version_type=$(prompt_version_type)

        # Suggest next version
        suggested_version=$(suggest_next_version "$current_version" "$version_type")
        print_info "Suggested next version: $suggested_version"

        # Confirm suggested version
        echo -n "Use suggested version $suggested_version? [Y/n]: "
        read -r use_suggested

        if [[ "$use_suggested" =~ ^[Nn]$ ]]; then
            echo -n "Enter custom version: "
            read -r custom_version
            if [ -z "$custom_version" ]; then
                print_error "No version specified"
                exit 1
            fi
            version="$custom_version"
        else
            version="$suggested_version"
        fi
    fi

    # Validate version format
    if ! validate_version "$version"; then
        exit 1
    fi

    # Add 'v' prefix if not present
    if [[ ! "$version" =~ ^v ]]; then
        version="v$version"
    fi

    print_header "Meetscribe Release Script"
    echo
    print_info "Version to release: $version"
    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN MODE - No changes will be made"
    fi
    echo

    # Confirm release
    if ! confirm "Ready to create release $version?"; then
        print_info "Release cancelled"
        exit 0
    fi

    # Check prerequisites
    if ! check_prerequisites; then
        print_error "Prerequisites check failed. Please resolve the issues above."
        exit 1
    fi

    echo

    # Update version
    if ! update_version "$version"; then
        print_error "Failed to update version. Exiting."
        exit 1
    fi

    # Confirm commit
    if ! confirm "Commit version change?"; then
        print_info "Rolling back version change..."
        git checkout pyproject.toml
        print_success "Changes rolled back"
        exit 0
    fi

    # Commit changes
    if ! commit_changes "$version"; then
        print_error "Failed to commit changes. Please check git status and resolve manually."
        exit 1
    fi

    # Confirm push
    if ! confirm "Push changes to main branch?"; then
        print_info "Rolling back commit..."
        git reset --hard HEAD~1
        git checkout pyproject.toml
        print_success "Changes rolled back"
        exit 0
    fi

    # Push to main
    if ! push_main; then
        print_error "Failed to push to main. Please push manually and then create the tag."
        exit 1
    fi

    # Confirm tag creation
    if ! confirm "Create and push tag $version?"; then
        print_info "Release completed without tag. You can create the tag manually:"
        print_info "  git tag -a $version -m \"Release $version\""
        print_info "  git push origin $version"
        show_next_steps "$version"
        exit 0
    fi

    # Create and push tag
    if ! create_tag "$version"; then
        print_error "Failed to create/push tag. You can do this manually:"
        print_info "  git tag -a $version -m \"Release $version\""
        print_info "  git push origin $version"
        exit 1
    fi

    echo
    show_next_steps "$version"

    if [ "$DRY_RUN" = true ]; then
        print_warning "This was a dry run - no actual changes were made"
    fi
}

# Change to project root directory
cd "$PROJECT_ROOT"

# Run main function
main "$@"
