#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
git_sync.py - Git Repository Synchronization Tool

A Python 2.7 implementation to synchronize multiple private GitLab repositories 
to GitHub/GitLab with support for full/incremental sync, branch mapping, 
LFS handling, and detailed reporting.

Usage:
    python git_sync.py --config config.yaml [--force-full] [-v]

Author: Cascade AI
Copyright 2025 Git Sync Tool Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys

# Fix encoding issues for Python 2.7
if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
import yaml
import subprocess
import argparse
import logging
import json
import re
import shutil
from datetime import datetime
from collections import defaultdict

# Global configuration and state
class GitSyncConfig(object):
    def __init__(self):
        # Global settings
        self.global_source_base = ""
        self.global_dest_base = ""
        self.global_commit_username = ""
        self.global_commit_useremail = ""
        self.global_auth_type = ""
        self.global_ssh_key = ""
        self.global_auth_user = ""
        self.global_auth_pass = ""
        self.global_lfs_file_threshold = 100
        self.global_lfs_threshold = 500
        self.global_workspace = ""
        
        # Repository configurations
        self.repositories = []
        
        # Runtime state
        self.force_full = False
        self.verbose = False

class Repository(object):
    def __init__(self, name):
        self.name = name
        self.source_repo = ""
        self.dest_repo = ""
        self.clean_history = False
        self.workspace = ""
        self.auth_type = ""
        self.auth_ssh_key = ""
        self.auth_user = ""
        self.auth_pass = ""
        self.enable_lfs = False
        self.lfs_file_threshold = 0
        self.lfs_threshold = 0
        self.branch_map = {}
        self.ignore_branches = []
        
        # Control whether to add original commit hash to commit message
        self.add_original_hash = False
        
        # Resolved values
        self.source_url = ""
        self.dest_url = ""
        self.workspace_path = ""

class GitSyncTool(object):
    def __init__(self):
        self.config = GitSyncConfig()
        self.logger = self._setup_logging()
        self.verbose = False  # Default to non-verbose mode
        self.report = {
            'repositories': {},
            'summary': {
                'total_repos': 0,
                'successful': 0,
                'failed': 0,
                'start_time': None,
                'end_time': None
            }
        }
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logger = logging.getLogger('git_sync')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_info(self, message):
        """Log info message"""
        import inspect
        frame = inspect.currentframe().f_back
        line_no = frame.f_lineno
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("[INFO:%d] %s" % (line_no, message))
        sys.stdout.flush()
    
    def log_error(self, message):
        """Log error message"""
        import inspect
        frame = inspect.currentframe().f_back
        line_no = frame.f_lineno
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("[ERROR:%d] %s" % (line_no, message))
        sys.stderr.flush()
    
    def log_warn(self, message):
        """Log warning message"""
        import inspect
        frame = inspect.currentframe().f_back
        line_no = frame.f_lineno
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("[WARN:%d] %s" % (line_no, message))
        sys.stdout.flush()
    
    def log_debug(self, message):
        """Log debug message"""
        if self.config and self.config.verbose:
            import inspect
            frame = inspect.currentframe().f_back
            line_no = frame.f_lineno
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print("[DEBUG:%d] %s" % (line_no, message))
            sys.stdout.flush()
    
    def check_dependencies(self):
        """Check required dependencies"""
        self.log_info("Checking dependencies...")
        
        required_tools = ['git']
        for tool in required_tools:
            try:
                subprocess.check_output([tool, '--version'], stderr=subprocess.STDOUT)
                self.log_debug("Found %s" % tool)
            except (subprocess.CalledProcessError, OSError):
                raise Exception("Required tool '%s' not found. Please install it." % tool)
        
        self.log_info("All dependencies satisfied.")
    
    def check_lfs_if_needed(self):
        """Check Git LFS availability when needed"""
        try:
            subprocess.check_output(['git', 'lfs', 'version'], stderr=subprocess.STDOUT)
            self.log_debug("Git LFS is available")
            return True
        except (subprocess.CalledProcessError, OSError):
            self.log_error("Git LFS is required but not available")
            return False
    
    def load_config(self, config_file):
        """Load and parse YAML configuration file"""
        self.log_info("Loading configuration from '%s'..." % config_file)
        
        if not os.path.exists(config_file):
            raise Exception("Configuration file '%s' not found." % config_file)
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Parse global configuration
        global_config = config_data.get('global', {})
        self.config.global_source_base = global_config.get('source_base_url', '')
        self.config.global_dest_base = global_config.get('dest_base_url', '')
        self.config.global_commit_username = global_config.get('commit_user_name', '')
        self.config.global_commit_useremail = global_config.get('commit_user_email', '')
        self.config.global_lfs_file_threshold = global_config.get('lfs_file_threshold_mb', 100)
        self.config.global_lfs_threshold = global_config.get('lfs_total_threshold_mb', 500)
        self.config.global_workspace = global_config.get('workspace', '')
        
        # Parse global auth with enhanced robustness
        global_auth = global_config.get('auth', {})
        if not isinstance(global_auth, dict):
            global_auth = {}
        self.config.global_auth_type = global_auth.get('type') or ''
        self.config.global_ssh_key = global_auth.get('ssh_private_key') or ''
        self.config.global_auth_user = global_auth.get('username') or ''
        self.config.global_auth_pass = global_auth.get('password') or ''
        
        # Parse repositories
        repositories_config = config_data.get('repositories', [])
        for repo_config in repositories_config:
            repo = Repository(repo_config['name'])
            
            # Basic settings (required fields)
            repo.source_repo = repo_config.get('source_repo', '')
            repo.dest_repo = repo_config.get('dest_repo', '')
            
            # Optional settings with global inheritance
            repo.clean_history = repo_config.get('clean_history') or False
            repo.workspace = repo_config.get('workspace', '') or self.config.global_workspace
            repo.enable_lfs = repo_config.get('enable_lfs') or False
            
            # LFS thresholds with global inheritance
            repo.lfs_file_threshold = repo_config.get('lfs_file_threshold_mb', 0) or self.config.global_lfs_file_threshold
            repo.lfs_threshold = repo_config.get('lfs_total_threshold_mb', 0) or self.config.global_lfs_threshold
            
            # Auth settings (inherit from global if not specified) with enhanced robustness
            repo_auth = repo_config.get('auth')
            if not isinstance(repo_auth, dict):
                repo_auth = {}
            repo.auth_type = repo_auth.get('type') or self.config.global_auth_type
            repo.auth_ssh_key = repo_auth.get('ssh_private_key') or self.config.global_ssh_key
            repo.auth_user = repo_auth.get('username') or self.config.global_auth_user
            repo.auth_pass = repo_auth.get('password') or self.config.global_auth_pass
            
            # Branch mapping
            branch_map = repo_config.get('branch_map', {})
            repo.branch_map = branch_map
            
            # Ignore branches
            ignore_branches = repo_config.get('ignore_branches', [])
            repo.ignore_branches = ignore_branches
            
            # Resolve URLs
            repo.source_url = self._resolve_url(repo.source_repo, self.config.global_source_base)
            repo.dest_url = self._resolve_url(repo.dest_repo, self.config.global_dest_base)
            
            # Resolve workspace (already inherited above, just convert to absolute path)
            if repo.workspace:
                repo.workspace_path = os.path.abspath(repo.workspace)
            else:
                raise Exception("Repository '%s' has no workspace defined (check global workspace setting)." % repo.name)
            
            # Ensure workspace directory exists
            if not os.path.exists(repo.workspace_path):
                os.makedirs(repo.workspace_path)
            
            self.config.repositories.append(repo)
            self.log_info("Repository '%s' configured." % repo.name)
        
        self.log_info("Configuration loaded successfully. Found %d repositories." % len(self.config.repositories))
    
    def _resolve_url(self, repo_url, base_url):
        """Resolve repository URL with base URL and authentication"""
        if not repo_url:
            raise Exception("Repository URL cannot be empty")
        
        # If repo_url is already a full URL, use it directly
        if repo_url.startswith(('http://', 'https://', 'git@', 'ssh://')):
            return repo_url
        
        # Handle local file paths (relative or absolute)
        if repo_url.startswith('./') or repo_url.startswith('../') or os.path.isabs(repo_url):
            # Convert to absolute path
            return os.path.abspath(repo_url)
        
        # If no base URL provided, cannot resolve relative URL
        if not base_url:
            raise Exception("Cannot resolve repository URL: %s" % repo_url)
        
        # Combine base URL with relative path
        if base_url.endswith('/'):
            return base_url + repo_url
        else:
            return base_url + '/' + repo_url
    
    def _add_auth_to_url(self, url, username, password):
        """Add authentication credentials to HTTP URL with proper URL encoding"""
        if not url.startswith(('http://', 'https://')):
            return url
        
        if not username or not password:
            return url
        
        # URL encode username and password to handle special characters
        try:
            # Python 2/3 compatibility for URL encoding
            if sys.version_info[0] == 2:
                import urllib
                encoded_username = urllib.quote(str(username), safe='')
                encoded_password = urllib.quote(str(password), safe='')
            else:
                import urllib.parse
                encoded_username = urllib.parse.quote(str(username), safe='')
                encoded_password = urllib.parse.quote(str(password), safe='')
        except Exception as e:
            self.log_warn("Failed to URL encode credentials: %s" % str(e))
            # Fallback to original values if encoding fails
            encoded_username = str(username)
            encoded_password = str(password)
        
        # Parse URL and insert encoded credentials
        if '://' in url:
            protocol, rest = url.split('://', 1)
            return "%s://%s:%s@%s" % (protocol, encoded_username, encoded_password, rest)
        
        return url
    
    def _normalize_url(self, url):
        """Normalize URL for comparison by removing trailing slashes and converting to lowercase"""
        if not url:
            return ""
        
        # Remove trailing slashes
        normalized = url.rstrip('/')
        
        # Convert to lowercase for case-insensitive comparison
        normalized = normalized.lower()
        
        # Remove .git suffix if present
        if normalized.endswith('.git'):
            normalized = normalized[:-4]
        
        return normalized
    
    def _remove_auth_from_url(self, url):
        """Remove authentication credentials from URL for comparison"""
        if not url:
            return ""
        
        # Handle HTTP/HTTPS URLs with embedded credentials
        if url.startswith(('http://', 'https://')):
            # Split protocol and rest
            protocol, rest = url.split('://', 1)
            
            # Check if there are credentials (username:password@)
            if '@' in rest:
                # Split at @ to separate credentials from host
                auth_part, host_part = rest.rsplit('@', 1)
                # Return URL without credentials
                return protocol + '://' + host_part
        
        # For SSH URLs or URLs without credentials, return as-is
        return url
    
    def _run_git_command(self, cmd, cwd=None, check_output=False):
        """Execute git command with proper error handling and output control"""
        try:
            if check_output:
                # Always capture output when check_output=True
                result = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT, shell=True)
                # Try multiple encoding methods to decode the output
                try:
                    return result.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        return result.decode('gbk').strip()
                    except UnicodeDecodeError:
                        return result.decode('utf-8', errors='ignore').strip()
            else:
                # Control output based on verbose mode
                if self.verbose:
                    # In verbose mode, allow git output to be displayed
                    subprocess.check_call(cmd, cwd=cwd, shell=True)
                else:
                    # In non-verbose mode, suppress stdout but capture stderr for error reporting
                    with open(os.devnull, 'w') as devnull:
                        subprocess.check_call(cmd, cwd=cwd, shell=True, stdout=devnull)
                    return None
        except subprocess.CalledProcessError as e:
            # Handle encoding issues in command and output
            try:
                if isinstance(cmd, unicode):
                    cmd_str = cmd.encode('utf-8')
                else:
                    cmd_str = cmd
            except:
                cmd_str = repr(cmd)
        
            try:
                error_msg = u"Git command failed: %s" % cmd_str
                # Always show error output regardless of verbose mode
                if hasattr(e, 'output') and e.output:
                    try:
                        error_output = e.output.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            error_output = e.output.decode('gbk')
                        except UnicodeDecodeError:
                            error_output = e.output.decode('utf-8', errors='ignore')
                    error_msg += u"\nOutput: %s" % error_output
            except UnicodeDecodeError:
                # Fallback to safe representation
                error_msg = "Git command failed: %s" % repr(cmd)
                if hasattr(e, 'output') and e.output:
                    error_msg += "\nOutput: %s" % repr(e.output)
            raise Exception(error_msg)
    
    def _get_file_size_mb(self, file_path):
        """Get file size in MB"""
        if not os.path.exists(file_path):
            return 0
        return os.path.getsize(file_path) / (1024.0 * 1024.0)
    
    def _should_use_lfs(self, file_path, threshold_mb):
        """Check if file should use LFS based on size threshold"""
        return self._get_file_size_mb(file_path) > threshold_mb
    
    def _setup_lfs_for_repo(self, repo_dir):
        """Setup Git LFS for repository"""
        if not self.check_lfs_if_needed():
            return False
        
        try:
            self._run_git_command('git lfs install', cwd=repo_dir)
            self.log_info("Git LFS initialized for repository")
            return True
        except Exception as e:
            self.log_error("Failed to setup LFS: %s" % str(e))
            return False
    
    def _get_branches(self, repo_dir, remote_only=True, remote_prefix='origin/'):
        """Get list of branches from repository
        
        Args:
            repo_dir: Repository directory path
            remote_only: If True, only get remote branches; if False, get all branches
            remote_prefix: Prefix for remote branches (e.g., 'origin/', 'source/')
        """
        try:
            if remote_only:
                # Get remote branches only
                cmd = 'git branch -r'
            else:
                # Get all branches (local + remote)
                cmd = 'git branch -a'
            
            output = self._run_git_command(cmd, cwd=repo_dir, check_output=True)
            
            # Debug: Log the raw git branch output
            self.log_debug("Raw git branch output for %s:" % remote_prefix)
            for line_num, line in enumerate(output.split('\n'), 1):
                if line.strip():
                    self.log_debug("  %d: '%s'" % (line_num, line))
            
            branches = []
            
            for line in output.split('\n'):
                line = line.strip()
                if not line or '->' in line or line.startswith('*'):
                    continue
                
                # Clean branch name - remove prefixes based on remote_prefix
                if remote_prefix and line.startswith(remote_prefix):
                    branch = line[len(remote_prefix):]
                elif not remote_prefix:
                    # Only use fallback logic when no specific remote_prefix is requested
                    branch = line.replace('origin/', '').replace('remotes/', '').replace('remotes/origin/', '')
                else:
                    # Skip branches that don't match the specified remote_prefix
                    continue
                
                # Skip HEAD reference
                if branch == 'HEAD':
                    continue
                
                if branch and branch not in branches:
                    branches.append(branch)
            
            # Special case: prioritize master or main branch to the top of the list
            if 'master' in branches:
                branches.remove('master')
                branches.insert(0, 'master')
            elif 'main' in branches:
                branches.remove('main')
                branches.insert(0, 'main')
            
            return branches if branches is not None else []
        except Exception as e:
            self.log_error("Failed to get branches: %s" % str(e))
            return []  # Always return empty list, never None
    
    def _should_ignore_branch(self, branch, ignore_list):
        """Check if branch should be ignored"""
        # Always ignore internal state management branch
        if branch == 'sync_state':
            return True
        
        # Safety check: handle None ignore_list
        if ignore_list is None:
            return False
        
        for ignore_pattern in ignore_list:
            if re.match(ignore_pattern.replace('*', '.*'), branch):
                return True
        return False
    
    def _map_branch_name(self, branch, branch_map):
        """Map branch name according to configuration"""
        # Safety check: handle None branch_map
        if branch_map is None:
            return branch
        return branch_map.get(branch, branch)
    
    def _get_sync_state(self, repo):
        """Get synchronization state from remote sync_state branch"""
        # Try to fetch sync state from remote sync_state branch
        try:
            return self._fetch_remote_sync_state(repo)
        except Exception as e:
            self.log_warn("Failed to fetch remote sync state: %s" % str(e))
            # If remote sync_state branch doesn't exist or fails, treat as no state
            self.log_info("No remote sync state found, treating as first-time sync")
            return {
                'last_sync': None,
                'synced_branches': {},
                'last_commits': {}
            }
    
    def _fetch_remote_sync_state(self, repo):
        """Fetch sync state from remote sync_state branch using unified work directory"""
        # Use unified work directory
        work_dir = os.path.join(repo.workspace_path, repo.name, 'sync_work')
        
        try:
            # Ensure work directory is set up with proper remotes
            self._setup_unified_work_dir(work_dir, repo)
            
            # Fetch latest changes from origin (destination repository)
            self._run_git_command('git fetch origin --prune', cwd=work_dir)
            
            # Check if sync_state branch exists on origin
            try:
                # First check if origin/sync_state exists
                self._run_git_command('git show-ref --verify refs/remotes/origin/sync_state', cwd=work_dir, check_output=True)
                # If it exists, checkout the branch
                self._run_git_command('git checkout -B sync_state origin/sync_state', cwd=work_dir)
                self.log_info("Found existing sync_state branch")
            except:
                # sync_state branch doesn't exist, return default state
                self.log_info("No sync_state branch found, using default state")
                return {
                    'last_sync': None,
                    'synced_branches': {},
                    'last_commits': {}
                }
            
            # Read sync_state.json from the branch
            state_file = os.path.join(work_dir, 'sync_state.json')
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.log_info("Successfully loaded sync state from remote")
                    return state
            else:
                self.log_info("No sync_state.json found in sync_state branch")
                return {
                    'last_sync': None,
                    'synced_branches': {},
                    'last_commits': {}
                }
                
        except Exception as e:
            # Handle potential encoding issues with Chinese characters
            try:
                error_msg = unicode(str(e), 'utf-8') if isinstance(str(e), str) else str(e)
            except:
                error_msg = repr(e)
            self.log_warn("Failed to fetch sync state: %s" % error_msg)
            return {
                'last_sync': None,
                'synced_branches': {},
                'last_commits': {}
            }
    
    def _setup_unified_work_dir(self, work_dir, repo):
        """Setup unified work directory with source and destination remotes"""
        try:
            if not os.path.exists(work_dir):
                # Create new work directory by cloning destination repository
                self.log_debug("Creating unified work directory")
                
                # Get destination URL with authentication
                dest_url_with_auth = self._add_auth_to_url(repo.dest_url, repo.auth_user, repo.auth_pass)
                
                # Clone destination repository as base
                self.log_info("Cloning destination repository: %s" % repo.dest_url)
                self._run_git_command('git clone "%s" "%s"' % (dest_url_with_auth, work_dir))
                
                # Add source repository as remote
                self._run_git_command('git remote add source "%s"' % repo.source_url, cwd=work_dir)
                
                self.log_info("Unified work directory created with source and origin remotes")
            else:
                # Verify and update existing work directory
                self.log_info("Verifying existing unified work directory")
                
                try:
                    # Check origin remote URL (compatible with older git versions)
                    origin_url = self._run_git_command('git config --get remote.origin.url', cwd=work_dir, check_output=True).strip()
                    # Remove authentication from URL for comparison
                    dest_url_with_auth = self._add_auth_to_url(repo.dest_url, repo.auth_user, repo.auth_pass)
                    origin_url_clean = self._remove_auth_from_url(origin_url)
                    
                    if self._normalize_url(origin_url_clean) != self._normalize_url(repo.dest_url):
                        # Wrong destination repository, recreate
                        self.log_warn("Destination repository mismatch, recreating work directory. Expected: %s, Found: %s" % (repo.dest_url, origin_url))
                        shutil.rmtree(work_dir)
                        self.log_info("Recreated work directory")
                        return self._setup_unified_work_dir(work_dir, repo)
                    
                    # Update origin URL with authentication
                    if dest_url_with_auth != origin_url:
                        self._run_git_command('git remote set-url origin "%s"' % dest_url_with_auth, cwd=work_dir)
                        self.log_info("Updated origin remote with authentication: %s" % repo.dest_url)
                    
                    # Check if source remote exists (compatible with older git versions)
                    try:
                        source_url = self._run_git_command('git config --get remote.source.url', cwd=work_dir, check_output=True).strip()
                        source_url_clean = self._remove_auth_from_url(source_url)
                        if self._normalize_url(source_url_clean) != self._normalize_url(repo.source_url):
                            # Update source remote
                            self._run_git_command('git remote set-url source "%s"' % repo.source_url, cwd=work_dir)
                            self.log_info("Updated source remote URL: %s" % repo.source_url)
                    except:
                        # Source remote doesn't exist, add it
                        self._run_git_command('git remote add source "%s"' % repo.source_url, cwd=work_dir)
                        self.log_info("Added source remote: %s" % repo.source_url)
                    
                except Exception as e:
                    # If verification fails, recreate directory
                    self.log_warn("Work directory verification failed: %s" % str(e))
                    shutil.rmtree(work_dir)
                    self.log_info("Recreating work directory")
                    return self._setup_unified_work_dir(work_dir, repo)
            
            # Configure git user for commits
            if self.config.global_commit_username:
                self._run_git_command('git config user.name "%s"' % self.config.global_commit_username, cwd=work_dir)
            if self.config.global_commit_useremail:
                self._run_git_command('git config user.email "%s"' % self.config.global_commit_useremail, cwd=work_dir)
            self.log_info("Unified work directory setup completed")
            return True
            
        except Exception as e:
            # Handle potential encoding issues with Chinese characters
            try:
                error_msg = unicode(str(e), 'utf-8') if isinstance(str(e), str) else str(e)
            except:
                error_msg = repr(e)
            self.log_error("Failed to setup unified work directory: %s" % error_msg)
            return False
    
    def _save_sync_state(self, repo, state):
        """Save synchronization state to remote sync_state branch using unified work directory"""
        try:
            self._push_remote_sync_state(repo, state)
            self.log_info("Sync state successfully saved to remote sync_state branch")
        except Exception as e:
            self.log_error("Failed to push sync state to remote: %s" % str(e))
            self.log_warn("Sync state could not be saved - will treat as first-time sync on next run")
    
    def _push_remote_sync_state(self, repo, state):
        """Push sync state to remote sync_state branch using unified work directory"""
        # Use unified work directory
        work_dir = os.path.join(repo.workspace_path, repo.name, 'sync_work')
        
        try:
            # Ensure work directory is set up with proper remotes
            if not self._setup_unified_work_dir(work_dir, repo):
                raise Exception("Failed to setup unified work directory")
            
            # Fetch latest changes from origin
            self._run_git_command('git fetch origin --prune', cwd=work_dir)
            
            # Handle sync_state branch checkout
            try:
                # Delete local branch if it exists
                try:
                    self._run_git_command('git branch -D sync_state', cwd=work_dir, check_output=True)
                except:
                    pass

                # Check if remote sync_state branch exists
                self._run_git_command('git show-ref --verify refs/remotes/origin/sync_state', cwd=work_dir, check_output=True)
                
                # Check if local sync_state branch exists
                try:
                    self._run_git_command('git show-ref --verify refs/heads/sync_state', cwd=work_dir, check_output=True)
                    # Local branch exists, switch to it and reset to remote
                    self._run_git_command('git checkout sync_state', cwd=work_dir)
                    self._run_git_command('git reset --hard origin/sync_state', cwd=work_dir)
                    self.log_info("Switched to existing local sync_state branch and reset to remote")
                except:
                    # Local branch doesn't exist, create from remote
                    self._run_git_command('git checkout -b sync_state origin/sync_state', cwd=work_dir)
                    self.log_info("Created local sync_state branch from remote")
            except:
                # Remote sync_state branch doesn't exist, create new orphan branch
                self._run_git_command('git checkout --orphan sync_state', cwd=work_dir)
                # Remove all files from the new branch
                try:
                    self._run_git_command('git rm -rf .', cwd=work_dir)
                except:
                    # If git rm fails (no files to remove), that's fine
                    pass
                self.log_info("Created new orphan sync_state branch")
            
            # Write sync_state.json to the branch
            state_file = os.path.join(work_dir, 'sync_state.json')
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Add and commit the state file
            self._run_git_command('git add sync_state.json', cwd=work_dir)
            
            # Check if there are changes to commit
            try:
                self._run_git_command('git diff --cached --exit-code', cwd=work_dir)
                # No changes, skip commit
                self.log_info("No changes in sync state, skipping commit")
                return
            except:
                # There are changes, proceed with commit
                pass
            
            # Commit the changes
            commit_message = "Update sync state - %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._run_git_command('git commit -m "%s"' % commit_message, cwd=work_dir)
            
            # Push to remote
            self._run_git_command('git push origin sync_state', cwd=work_dir)
            
            self.log_info("Successfully pushed sync state to remote")
            
        except Exception as e:
            # Handle potential encoding issues with Chinese characters
            try:
                error_msg = unicode(str(e), 'utf-8') if isinstance(str(e), str) else str(e)
            except:
                error_msg = repr(e)
            self.log_error("Failed to push sync state: %s" % error_msg)
            raise
    
    def _get_commit_info(self, repo_dir, branch, commit_hash=None, remote_name='origin'):
        """Get commit information
        
        Args:
            repo_dir: Repository directory path
            branch: Branch name
            commit_hash: Specific commit hash (optional)
            remote_name: Remote name ('origin' for dest repo, 'source' for source repo)
        """
        try:
            if commit_hash:
                # For commit hash, use git show command
                # Use -s instead of --no-patch for better compatibility with older git versions
                cmd = 'git show --format="%%H|%%an|%%ae|%%ad|%%s" -s "%s"' % commit_hash
                output = self._run_git_command(cmd, cwd=repo_dir, check_output=True)
            else:
                # For branch names, try comprehensive reference formats
                # Order matters: try most specific first, then fallback to less specific
                branch_refs = [
                    "refs/remotes/%s/%s" % (remote_name, branch),  # Remote tracking branch (primary for unified work dir)
                    "refs/heads/%s" % branch,                      # Local branch (if checked out)
                    "%s/%s" % (remote_name, branch),               # Short remote reference
                    "remotes/%s/%s" % (remote_name, branch),       # Alternative remote format
                    branch                                         # Bare branch name (fallback)
                ]
                
                output = None
                successful_ref = None
                
                for ref in branch_refs:
                    try:
                        # For branch references, don't use -- separator as it's for paths
                        cmd = 'git log -1 --format="%%H|%%an|%%ae|%%ad|%%s" "%s"' % ref
                        test_output = self._run_git_command(cmd, cwd=repo_dir, check_output=True)
                        if test_output and test_output.strip():
                            output = test_output
                            successful_ref = ref
                            self.log_info("Found commit info for branch '%s' using reference '%s'" % (branch, ref))
                            break
                    except Exception as ref_error:
                        self.log_info("Reference '%s' failed: %s" % (ref, str(ref_error)))
                        continue
                
                if not output:
                    # Last resort: try to list all refs and find a match
                    try:
                        self.log_info("Attempting to find branch '%s' in all available references..." % branch)
                        refs_cmd = 'git for-each-ref --format="%(refname)" refs/'
                        all_refs = self._run_git_command(refs_cmd, cwd=repo_dir, check_output=True)
                        
                        matching_refs = []
                        for ref_line in all_refs.split('\n'):
                            if ref_line.strip() and branch in ref_line:
                                matching_refs.append(ref_line.strip())
                        
                        if matching_refs:
                            self.log_info("Found potential matching refs: %s" % ', '.join(matching_refs))
                            # Try the first matching ref
                            cmd = 'git log -1 --format="%%H|%%an|%%ae|%%ad|%%s" "%s"' % matching_refs[0]
                            output = self._run_git_command(cmd, cwd=repo_dir, check_output=True)
                            successful_ref = matching_refs[0]
                        else:
                            self.log_debug("No matching references found for branch '%s'" % branch)
                    except Exception as search_error:
                        self.log_debug("Reference search failed: %s" % str(search_error))
                
                if not output:
                    self.log_error("Could not find commit info for branch '%s' with any reference format" % branch)
                    return None
            
            if not output or not output.strip():
                return None
                
            parts = output.strip().split('|', 4)
            
            if len(parts) >= 5:
                return {
                    'hash': parts[0],
                    'author': parts[1],
                    'email': parts[2],
                    'date': parts[3],
                    'message': parts[4]
                }
            else:
                self.log_debug("Invalid commit info format: %s" % output)
                return None
                
        except Exception as e:
            self.log_error("Failed to get commit info for branch '%s': %s" % (branch, str(e)))
        
        return None
    
    def _calculate_changes_size(self, repo_dir, from_commit=None, to_commit=None):
        """Calculate total size of changes between commits, handling LFS files correctly"""
        try:
            if from_commit and to_commit:
                # Use --numstat to get detailed change info including binary file detection
                cmd = 'git diff --numstat "%s".."%s"' % (from_commit, to_commit)
            elif from_commit:
                # Calculate changes from specific commit to HEAD
                cmd = 'git diff --numstat "%s"..HEAD' % from_commit
            else:
                cmd = 'git ls-files'
            
            output = self._run_git_command(cmd, cwd=repo_dir, check_output=True)
            total_size = 0
            
            for line in output.split('\n'):
                if line.strip():
                    if from_commit:
                        # git diff --numstat format: "additions deletions filename"
                        # For binary files shows: "- - filename"
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            additions, deletions, filename = parts[0], parts[1], parts[2]
                            full_path = os.path.join(repo_dir, filename)
                            
                            if os.path.exists(full_path):
                                # Get actual file size (handle LFS pointer files)
                                actual_size = self._get_actual_file_size_mb(full_path)
                                total_size += actual_size
                    else:
                        # List all files
                        full_path = os.path.join(repo_dir, line.strip())
                        if os.path.exists(full_path):
                            actual_size = self._get_actual_file_size_mb(full_path)
                            total_size += actual_size
            
            self.log_info("Calculated changes size: %.2f MB" % total_size)
            return total_size
        except Exception as e:
            self.log_debug("Failed to calculate changes size: %s" % str(e))
            return 0
    
    def _is_lfs_pointer_file(self, file_path):
        """Check if file is an LFS pointer file"""
        try:
            # LFS pointer files are typically very small (<1KB)
            if os.path.getsize(file_path) > 1024:
                return False
            
            with open(file_path, 'r') as f:
                first_line = f.readline().strip()
                return first_line.startswith('version https://git-lfs.github.com/spec/')
        except:
            return False
    
    def _get_lfs_file_actual_size(self, file_path):
        """Get actual size of LFS file from pointer file"""
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('size '):
                        size_bytes = int(line.split()[1])
                        return size_bytes / (1024.0 * 1024.0)  # Convert to MB
        except:
            pass
        return 0
    
    def _get_actual_file_size_mb(self, file_path):
        """Get file size in MB for Git operations (LFS files use pointer size)
        
        For LFS files, returns the pointer file size since only the pointer
        is stored in Git repository and affects push/pull limits.
        """
        if not os.path.exists(file_path):
            return 0
        
        # For both LFS pointer files and regular files, use the actual file size on disk
        # LFS pointer files are small (~200-500 bytes) which is what gets pushed to Git
        return self._get_file_size_mb(file_path)
    
    def _is_empty_repository(self, repo_dir):
        """Check if repository is empty (no commits)"""
        try:
            # Try to get HEAD commit - will fail if repository is empty
            self._run_git_command('git rev-parse HEAD', cwd=repo_dir, check_output=True)
            return False
        except:
            # If rev-parse HEAD fails, repository is empty
            return True
    
    def sync_repository(self, repo):
        """Synchronize a single repository"""
        self.log_info("=" * 60)
        self.log_info("Starting synchronization for repository: %s" % repo.name)
        
        repo_report = {
            'status': 'failed',
            'mode': 'unknown',
            'branches_synced': 0,
            'branches_skipped': 0,
            'new_branches': 0,
            'ignored_branches': [],
            'commits_synced': 0,
            'lfs_triggered': False,
            'error': None,
            'start_time': datetime.now().isoformat()
        }
        
        try:
            # Get sync state
            sync_state = self._get_sync_state(repo)
            
            # Determine sync mode
            is_full_sync = self.config.force_full or sync_state['last_sync'] is None
            sync_mode = 'full' if is_full_sync else 'incremental'
            repo_report['mode'] = sync_mode
            
            self.log_info("Sync mode: %s" % sync_mode.upper())
            
            # Setup unified work directory for getting branches
            work_dir = os.path.join(repo.workspace_path, repo.name, 'sync_work')
            if not self._setup_unified_work_dir(work_dir, repo):
                raise Exception("Failed to setup unified work directory")
            
            # Fetch latest changes from source remote
            self._run_git_command('git fetch source --prune', cwd=work_dir)
            # Fetch all tags
            self._run_git_command('git fetch source --tags', cwd=work_dir)
            
            # Get branches from source remote
            source_branches = self._get_branches(work_dir, remote_only=True, remote_prefix='source/')
            
            # Safety check: ensure source_branches is not None
            if source_branches is None:
                self.log_error("Failed to get branches from source repository")
                raise Exception("Cannot retrieve source branches")
            
            self.log_info("Found %d branches in source repository" % len(source_branches))
            # Debug: Log the actual branch names retrieved
            self.log_debug("Source branches: %s" % ', '.join(source_branches))
            
            # Filter branches
            branches_to_sync = []
            ignored_branches = []
            for branch in source_branches:
                if self._should_ignore_branch(branch, repo.ignore_branches):
                    ignored_branches.append(branch)
                    self.log_info("Ignoring branch: %s" % branch)
                    continue
                branches_to_sync.append(branch)
            
            # Record ignored branches in report
            repo_report['ignored_branches'] = ignored_branches
            
            self.log_info("Will sync %d branches (after filtering)" % len(branches_to_sync))
            
            # Fetch latest changes from both remotes once for all branches
            self.log_info("Fetching latest changes from destination repositories")
            self._run_git_command('git fetch origin --prune', cwd=work_dir)
            
            # Sync each branch
            synced_count = 0
            skipped_count = 0
            new_branches_count = 0
            failed_count = 0
            
            for branch in branches_to_sync:
                try:
                    mapped_branch = self._map_branch_name(branch, repo.branch_map)
                    self.log_info("Syncing branch: %s -> %s" % (branch, mapped_branch))
                    # Debug: Log branch mapping details
                    if branch != mapped_branch:
                        self.log_debug("Branch mapping applied: '%s' mapped to '%s'" % (branch, mapped_branch))
                    else:
                        self.log_debug("No branch mapping for '%s', using original name" % branch)
                    
                    # Check if this is a new branch or mapping changed
                    is_new_branch = branch not in sync_state['synced_branches']
                    mapping_changed = (branch in sync_state['synced_branches'] and 
                                     sync_state['synced_branches'][branch] != mapped_branch)
                    
                    if is_new_branch:
                        new_branches_count += 1
                        self.log_info("New branch detected: %s" % branch)
                    elif mapping_changed:
                        new_branches_count += 1
                        self.log_info("Branch mapping changed: %s (%s -> %s)" % 
                                    (branch, sync_state['synced_branches'][branch], mapped_branch))
                    
                    # Perform branch sync
                    sync_result = self._sync_branch(repo, branch, mapped_branch, is_full_sync or is_new_branch or mapping_changed, sync_state)
                    if sync_result == 'synced':
                        synced_count += 1
                        sync_state['synced_branches'][branch] = mapped_branch
                    elif sync_result == 'skipped':
                        skipped_count += 1
                    elif sync_result == 'failed':
                        failed_count += 1
                        self.log_error("Branch %s synchronization failed" % branch)

                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    self.log_error("Failed to sync branch %s: %s" % (branch, str(e)))
                    self.log_error("Full traceback:\n%s" % error_details)
                    continue
            
            try:
                # push all tags at once
                self.log_info("pushing all tags")
                self._run_git_command('git push origin --tags', cwd=work_dir)
            except Exception as push_error:
                self.log_warn("Failed to push tags: %s" % str(push_error))
            
            # Update sync state only if branches were actually synced
            if synced_count > 0:
                sync_state['last_sync'] = datetime.now().isoformat()
                self._save_sync_state(repo, sync_state)
                self.log_info("Sync state updated with new timestamp")
            else:
                self.log_info("No branches synced, sync state unchanged")
            
            # Update report
            # Set status based on whether there were any failures
            if failed_count > 0:
                repo_report['status'] = 'partial_success' if synced_count > 0 else 'failed'
            else:
                repo_report['status'] = 'success'
            
            repo_report['branches_synced'] = synced_count
            repo_report['branches_skipped'] = skipped_count
            repo_report['new_branches'] = new_branches_count
            repo_report['branches_failed'] = failed_count
            repo_report['end_time'] = datetime.now().isoformat()
            
            if failed_count > 0:
                self.log_info("Repository '%s' synchronized with failures!" % repo.name)
                self.log_info("Branches synced: %d, Skipped: %d, New branches: %d, Failed: %d" % (synced_count, skipped_count, new_branches_count, failed_count))
            else:
                self.log_info("Repository '%s' synchronized successfully!" % repo.name)
                self.log_info("Branches synced: %d, Skipped: %d, New branches: %d" % (synced_count, skipped_count, new_branches_count))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            repo_report['error'] = str(e)
            self.log_error("Failed to sync repository '%s': %s" % (repo.name, str(e)))
            self.log_error("Full traceback:\n%s" % error_details)
        
        self.report['repositories'][repo.name] = repo_report
        return repo_report['status'] == 'success'
    
    def _sync_branch(self, repo, source_branch, dest_branch, is_full_sync, sync_state):
        """Synchronize a single branch"""
        try:
            state_key = '%s->%s' % (source_branch, dest_branch) if source_branch != dest_branch else source_branch

            # Use unified working directory (already set up at repository level)
            work_dir = os.path.join(repo.workspace_path, repo.name, 'sync_work')
            
            # Debug: Log the actual branch names being used
            self.log_info("Syncing: source_branch='%s' -> dest_branch='%s'" % (source_branch, dest_branch))
            
            # Get source commit info from unified work directory
            source_commit = self._get_commit_info(work_dir, source_branch, remote_name='source')
            if not source_commit:
                self.log_error("Cannot get commit info for branch: %s" % source_branch)
                return 'failed'
            
            # Check if we need to sync (for incremental mode)
            # Safety check: ensure sync_state structure is valid
            if not sync_state or 'last_commits' not in sync_state or sync_state['last_commits'] is None:
                self.log_warn("Invalid sync state structure, treating as first sync")
                last_synced_commit = None
            elif is_full_sync:
                last_synced_commit = None
            else:
                last_synced_commit = sync_state['last_commits'].get(state_key)
            
            if last_synced_commit and last_synced_commit == source_commit['hash']:
                self.log_info("Branch %s is up to date, skipping" % source_branch)
                return 'skipped'
            
            # Initialize add_original_hash parameter based on dest branch consistency
            repo.add_original_hash = False  # Default to False
            
            # Check if dest branch's last commit matches sync state commit
            try:
                # First check if destination branch exists in origin
                self._run_git_command('git show-ref --verify refs/remotes/origin/%s' % dest_branch, cwd=work_dir, check_output=True)
                
                # Get current HEAD of destination branch
                dest_head_cmd = 'git rev-parse origin/%s' % dest_branch
                dest_head = self._run_git_command(dest_head_cmd, cwd=work_dir, check_output=True).strip()
                
                # Compare with sync state commit
                if last_synced_commit and dest_head != last_synced_commit:
                    # Dest branch has diverged from sync state, need to add original hash
                    repo.add_original_hash = True
                    self.log_info("Dest branch has diverged from sync state, will add original hash to commit messages")
                else:
                    self.log_info("Dest branch is consistent with sync state, will preserve original commit messages")
            except Exception as e:
                # Dest branch doesn't exist or can't be determined - this is likely a new branch
                repo.add_original_hash = False
                self.log_info("Dest branch does not exist or cannot be determined, treating as new branch - will preserve original commit messages")
            
            try:
                # Check if destination repository is empty
                is_empty_repo = self._is_empty_repository(work_dir)
                
                # Handle different sync scenarios
                if repo.clean_history:
                    # Full sync with clean history - create orphan branch
                    self.log_info("Performing full sync with clean history for branch: %s" % dest_branch)
                    
                    # Create orphan branch
                    self._run_git_command('git checkout --orphan temp_clean', cwd=work_dir)
                    self._run_git_command('git rm -rf .', cwd=work_dir)
                    
                    # Copy files from source branch
                    self._run_git_command('git checkout %s -- .' % source_commit['hash'], cwd=work_dir)
                    
                    # Check for large files and setup LFS if needed (auto-enable if required)
                    self._check_and_setup_lfs(work_dir, repo)
                    
                    # Commit with appropriate message
                    commit_message = "[SYNC] %s\n\nOriginal SHA: %s" % (source_commit['message'], source_commit['hash'])
                    
                    self._run_git_command('git add .', cwd=work_dir)
                    self._run_git_command('git commit -m "%s"' % commit_message.replace('"', '\"'), cwd=work_dir)
                    
                    # Replace original branch
                    self._run_git_command('git branch -D "%s"' % dest_branch, cwd=work_dir)
                    self._run_git_command('git branch -m temp_clean "%s"' % dest_branch, cwd=work_dir)
                    
                    # Push clean history to destination repository
                    try:
                        self._run_git_command('git push origin "%s" --force' % dest_branch, cwd=work_dir)
                    except Exception as push_error:
                        self.log_error("Failed to push clean history for branch %s: %s" % (dest_branch, str(push_error)))
                        return 'failed'
                    
                else:
                    # Incremental sync or full sync without clean history
                    if is_full_sync:
                        self.log_info("Performing full sync (preserve history) for branch: %s" % dest_branch)

                        # Delete local branch if it exists
                        try:
                            self._run_git_command('git branch -D "%s"' % dest_branch, cwd=work_dir, check_output=True)
                        except:
                            pass

                        # Delete remote branch if it exists
                        try:
                            self._run_git_command('git branch -d -r "%s"' % dest_branch, cwd=work_dir, check_output=True)
                        except:
                            pass

                    else:
                        self.log_info("Performing incremental sync for branch: %s" % dest_branch)
                    
                    # For existing repository, perform cherry-pick based sync
                    self.log_info("Syncing branch %s using cherry-pick strategy" % dest_branch)
                    
                    # Clean working directory to avoid checkout conflicts
                    try:
                        # Check if HEAD exists before trying to reset
                        self._run_git_command('git rev-parse --verify HEAD', cwd=work_dir, check_output=True)
                        # HEAD exists, safe to reset
                        self._run_git_command('git reset --hard HEAD', cwd=work_dir)
                        self.log_debug("Reset working directory to HEAD")
                    except Exception as reset_error:
                        self.log_debug("HEAD not found or reset failed (likely empty repo): %s" % str(reset_error))
                        pass

                    try:
                        # Clean untracked files and directories
                        self._run_git_command('git clean -fdx', cwd=work_dir)
                        self.log_debug("Cleaned untracked files from working directory")
                    except Exception as clean_error:
                        self.log_debug("Clean untracked files failed: %s" % str(clean_error))
                        pass

                    # Ensure we're on the correct destination branch
                    try:
                        # Check if destination branch exists in origin
                        self._run_git_command('git show-ref --verify refs/remotes/origin/%s' % dest_branch, cwd=work_dir, check_output=True)
                        # Origin branch exists, check if local branch exists
                        try:
                            self._run_git_command('git show-ref --verify refs/heads/%s' % dest_branch, cwd=work_dir, check_output=True)
                            # Local branch exists, switch and reset to origin
                            self._run_git_command('git checkout --force %s' % dest_branch, cwd=work_dir)
                            self._run_git_command('git reset --hard origin/%s' % dest_branch, cwd=work_dir)
                            self.log_info("Switched to existing local branch %s and reset to origin" % dest_branch)
                        except:
                            # Local branch doesn't exist, create from origin
                            self._run_git_command('git checkout --force -b "%s" origin/%s' % (dest_branch, dest_branch), cwd=work_dir)
                            self.log_info("Created local branch %s from origin/%s" % (dest_branch, dest_branch))
                    except:
                        # Origin branch doesn't exist, create new branch from source
                        try:
                        # Get current branch name (handle empty repository case)
                            has_rename = False
                            try:
                                current_branch = self._run_git_command('git rev-parse --abbrev-ref HEAD', cwd=work_dir, check_output=True).strip()
                            except Exception as head_error:
                                # Handle empty repository or invalid HEAD case
                                self.log_debug("Cannot get current branch (likely empty repo): %s" % str(head_error))
                                current_branch = None
                            if current_branch and current_branch == dest_branch:
                                # Rename current branch to temp if it's the same as dest_branch
                                self._run_git_command('git branch -m temp', cwd=work_dir)
                                has_rename = True
                                self.log_info("Renamed current branch %s to temp" % dest_branch)
                            else:
                                # Delete local branch if it exists (skip if empty repo)
                                if current_branch:  # Only try to delete if we have a valid current branch
                                    try:
                                        self._run_git_command('git branch -D "%s"' % dest_branch, cwd=work_dir, check_output=True)
                                    except:
                                        pass
                                else:
                                    self.log_debug("Skipping branch deletion in empty repository")

                            self._run_git_command('git checkout --force -b "%s" source/%s' % (dest_branch, source_branch), cwd=work_dir)
                            self._run_git_command('git reset --hard "%s"' % source_commit['hash'], cwd=work_dir)
                            self.log_info("Created new branch %s from source/%s" % (dest_branch, source_branch))

                            if has_rename:
                                # Delete temp branch if it exists
                                try:
                                    self._run_git_command('git branch -D temp', cwd=work_dir, check_output=True)
                                except:
                                    pass

                            # Update is_full_sync flag
                            is_full_sync = True
                        except Exception as e:
                            self.log_error("Failed to create branch %s: %s" % (dest_branch, str(e)))
                            return 'failed'
                    
                    # Check total size of changes
                    if is_full_sync:
                        # Full sync: calculate size of all files
                        total_size = self._calculate_changes_size(work_dir)
                    elif last_synced_commit:
                        # Incremental sync: calculate size of changes since last sync
                        total_size = self._calculate_changes_size(work_dir, from_commit=last_synced_commit, to_commit=source_commit['hash'])
                    else:
                        # First time sync: calculate size of all files
                        total_size = self._calculate_changes_size(work_dir)

                    if total_size > repo.lfs_threshold:
                        # Split into individual commits (each commit is pushed individually)
                        self.log_info("Large changes detected (%.2f MB), syncing commit by commit" % total_size)
                        self._sync_step_by_step(work_dir, repo, source_branch, last_synced_commit, source_commit['hash'], is_full_sync)
                    else:
                        if is_full_sync:
                            # Full sync: check all files
                            lfs_enabled = self._check_and_setup_lfs(work_dir, repo)
                        else:
                            # Incremental sync: check changed files since last sync
                            lfs_enabled = self._check_and_setup_lfs(work_dir, repo, from_ref=last_synced_commit, to_ref='source/%s' % source_branch)

                        if not lfs_enabled:
                            try:
                                # No LFS needed, cherry-pick all commits at once
                                if last_synced_commit:
                                    self._run_git_command('git cherry-pick %s..%s' % (last_synced_commit, source_commit['hash']), cwd=work_dir)
                                elif not is_full_sync:
                                    # Check if this commit already exists in current branch
                                    try:
                                        current_head = self._run_git_command('git rev-parse HEAD', cwd=work_dir, check_output=True).strip()
                                        if current_head == source_commit['hash']:
                                            self.log_info("Branch is already up to date, no commits to cherry-pick")
                                        else:
                                            self._run_git_command('git cherry-pick %s' % source_commit['hash'], cwd=work_dir)
                                    except Exception as e:
                                        # If we can't get HEAD, continue with cherry-pick
                                        self.log_error("Failed to get HEAD, continue with cherry-pick: %s" % str(e))
                                        pass
                            except Exception as e:
                                try:
                                    self.log_error("Failed to cherry-pick commits: %s" % str(e))
                                    self._run_git_command('git cherry-pick --abort', cwd=work_dir)
                                except:
                                    # If abort fails, try to reset to clean state
                                    try:
                                        self._run_git_command('git reset --hard HEAD', cwd=work_dir)
                                        self._run_git_command('git clean -fd', cwd=work_dir)
                                        self.log_info("Reset to clean state after cherry-pick failure")
                                    except:
                                        pass

                                return 'failed'
                        
                            # Push batch changes to destination repository
                            try:
                                if is_full_sync:
                                    self._run_git_command('git push origin "%s" --force' % dest_branch, cwd=work_dir)
                                else:
                                    self._run_git_command('git push origin "%s"' % dest_branch, cwd=work_dir)
                            except Exception as push_error:
                                self.log_error("Failed to push branch %s: %s" % (dest_branch, str(push_error)))
                                return 'failed'

                        else:
                            try:
                                self._sync_step_by_step(work_dir, repo, source_branch, last_synced_commit, source_commit['hash'], is_full_sync)
                            except Exception as step_error:
                                self.log_error("Failed to sync step by step for branch %s: %s" % (source_branch, str(step_error)))
                                return 'failed'

                # Update sync state only after successful push
                sync_state['last_commits'][state_key] = source_commit['hash']
                
                self.log_info("Branch %s -> %s synchronized successfully" % (source_branch, dest_branch))
                return 'synced'
                
            except Exception as e:
                self.log_error("Failed to sync branch %s: %s" % (source_branch, str(e)))
                return 'failed'

        except Exception as e:
            self.log_error("Failed to sync branch %s: %s" % (source_branch, str(e)))
            return 'failed'

    _BINARY_EXTS = {'.tar', '.gz', '.zip', '.jar', '.dll', '.so', '.lib', '.exe'}

    def _is_relevant_file(self, rel_path):
        """
        Check if a file is relevant for sync.
        """
        _, ext = os.path.splitext(rel_path.lower())
        return ext in self._BINARY_EXTS

    def _get_changed_files_between_refs(self, work_dir, from_ref, to_ref):
        """
        List files added, copied, modified or renamed between from_ref and to_ref.
        Returns paths relative to work_dir.
        """
        # Build command as string to avoid list/unicode issues
        cmd = 'git diff --diff-filter=ACMR --name-only "%s" "%s"' % (from_ref, to_ref)
        try:
            output = self._run_git_command(cmd, cwd=work_dir, check_output=True)
        except Exception as e:
            self.log_error("Failed to list changed files: %s" % str(e))
            return []

        all_files = [line.strip() for line in output.splitlines() if line.strip()]
        return [f for f in all_files if self._is_relevant_file(f)]

    def _get_blob_size_mb(self, work_dir, ref, rel_path):
        """
        Get the size in MB of the blob at ref:rel_path without checking it out.
        """
        try:
            cmd = 'git rev-parse "%s:%s"' % (ref, rel_path)
            blob_id = self._run_git_command(cmd, cwd=work_dir, check_output=True).strip()
        except Exception as e:
            self.log_warn("Could not resolve blob for %s:%s: %s" % (ref, rel_path, str(e)))
            return 0.0

        try:
            cmd = 'git cat-file -s "%s"' % blob_id
            size_bytes = int(self._run_git_command(cmd, cwd=work_dir, check_output=True).strip())
        except Exception as e:
            self.log_warn("Could not get blob size for %s: %s" % (blob_id, str(e)))
            return 0.0

        return size_bytes / (1024.0 * 1024.0)

    def _check_and_setup_lfs(self, work_dir, repo, from_ref=None, to_ref="HEAD"):
        """
        Detect large files and configure Git LFS.

        - Full-scan mode (from_ref is None): walk the working tree on disk.
        - Incremental mode (from_ref provided): list files changed
          between from_ref and to_ref (which can be any branch or commit).
        Returns True if LFS was initialized or patterns added; False otherwise.
        """
        lfs_needed = False

        # 1) Gather candidates
        if from_ref:
            candidates = self._get_changed_files_between_refs(work_dir, from_ref, to_ref)
            mode = "Incremental (%s → %s)" % (from_ref, to_ref)
        else:
            candidates = []
            for root, _, files in os.walk(work_dir):
                if ".git" in root:
                    continue
                for fn in files:
                    rel = os.path.relpath(os.path.join(root, fn), work_dir)
                    if self._is_relevant_file(rel):
                        candidates.append(rel)
            mode = "Full-scan"

        self.log_info("Starting LFS check [%s], %d files" % (mode, len(candidates)))

        # 2) Inspect each
        for rel in candidates:
            if from_ref:
                # skip if doesn't exist at to_ref
                cmd = 'git ls-tree --name-only "%s" -- "%s"' % (to_ref, rel)
                exists = self._run_git_command(cmd, cwd=work_dir, check_output=True).strip()
                if not exists:
                    self.log_debug("Skipping removed: %s" % rel)
                    continue
                size_mb = self._get_blob_size_mb(work_dir, to_ref, rel)
            else:
                abs_path = os.path.join(work_dir, rel)
                if not os.path.exists(abs_path):
                    self.log_debug("Skipping missing: %s" % rel)
                    continue
                size_mb = self._get_file_size_mb(abs_path)

            # 3) Threshold check
            if size_mb >= repo.lfs_file_threshold:
                tracked = self._is_file_lfs_tracked(work_dir, rel)
                status = "already LFS" if tracked else "will track"
                self.log_info("Large file: %s (%.2f MB) – %s" % (rel, size_mb, status))

                if not lfs_needed:
                    if not self._setup_lfs_for_repo(work_dir):
                        self.log_error("LFS init failed, large files will commit normally")
                        return False
                    lfs_needed = True

                if not tracked:
                    try:
                        self._run_git_command('git lfs track "%s"' % rel, cwd=work_dir)
                        self.log_info("Added LFS rule: %s" % rel)
                    except Exception as e:
                        self.log_warn("LFS track failed for %s: %s" % (rel, str(e)))

        # 4) Stage .gitattributes if needed
        if lfs_needed:
            try:
                self._run_git_command('git add .gitattributes', cwd=work_dir)
            except Exception as e:
                self.log_warn("Failed to stage .gitattributes: %s" % str(e))

        return lfs_needed

    def _is_file_lfs_tracked(self, work_dir, file_path):
        """Check if a file is already tracked by LFS"""
        try:
            # Use git check-attr to see if file has lfs filter
            output = self._run_git_command('git check-attr filter "%s"' % file_path, cwd=work_dir, check_output=True)
            # Output format: "file_path: filter: lfs" if tracked by LFS
            return 'filter: lfs' in output
        except:
            # If command fails or file doesn't exist, assume not LFS tracked
            return False
    
    def _sync_single_commit(self, work_dir, repo, commit_hash, source_branch, force_push=False):
        """Sync a single commit
        
        Args:
            work_dir: Working directory path
            repo: Repository configuration
            commit_hash: Hash of commit to sync
            source_branch: Source branch name
            force_push: Whether to use --force when pushing (default: False)
        """
        try:
            # Get current commit hash
            current_commit = self._run_git_command('git rev-parse HEAD', cwd=work_dir, check_output=True).strip()

            # Get commit info
            commit_info = self._get_commit_info(work_dir, source_branch, commit_hash, remote_name='source')
            if not commit_info:
                self.log_error("Cannot get commit info for: %s" % commit_hash)
                return False
            
            # Cherry-pick the commit
            if current_commit != commit_hash:
                self._run_git_command('git cherry-pick %s' % commit_hash, cwd=work_dir)
            
            # Check for large files and setup LFS if needed (auto-enable if required)
            self.log_debug("Checking for large files and setup LFS if needed")
            lfs_enabled = self._check_and_setup_lfs(work_dir, repo, current_commit)
            self.log_debug("LFS enabled: %s" % lfs_enabled)

            # Update commit message based on add_original_hash setting or LFS usage
            if lfs_enabled or repo.add_original_hash:
                # LFS was enabled or hash addition is required, include original SHA
                new_message = "[SYNC] %s\n\nOriginal SHA: %s" % (commit_info['message'], commit_hash)
                self._run_git_command('git commit --amend -m "%s"' % new_message.replace('"', '\"'), cwd=work_dir)
                repo.add_original_hash = True
                self.log_debug("Updated commit message with original SHA")
            else:
                # No LFS and no hash addition needed, keep original commit message and SHA unchanged
                self.log_debug("Keeping original commit message and SHA")
            
            # Push individual commit to avoid large data transfer
            try:
                if force_push:
                    self._run_git_command('git push origin HEAD --force', cwd=work_dir)
                    self.log_debug("Force pushed commit: %s" % commit_hash[:8])
                else:
                    self._run_git_command('git push origin HEAD', cwd=work_dir)
                    self.log_debug("Pushed commit: %s" % commit_hash[:8])
            except Exception as push_error:
                self.log_error("Failed to push commit %s: %s" % (commit_hash[:8], str(push_error)))
                return False
            
            self.log_debug("Synced and pushed commit: %s" % commit_hash[:8])
            return True
            
        except Exception as e:
            self.log_error("Failed to sync commit %s: %s" % (commit_hash, str(e)))
            return False

    def _sync_step_by_step(self, work_dir, repo, source_branch, last_synced_commit, to_commit, is_full_sync):
        """
        Sync a branch commit-by-commit up to a specified ref.

        Args:
            work_dir: Path to the working directory.
            repo: Repository config object.
            source_branch: Name of the source branch (e.g., "main").
            last_synced_commit: SHA of the last synced commit (for incremental).
            to_commit: Target commit or ref to sync up to.
            is_full_sync: If True, ignore last_synced_commit and do full history.
        """
        try:
            # Determine the end reference: explicit to_commit or remote branch tip
            end_ref = to_commit or "source/%s" % source_branch

            # Build the git-log range specifier
            if last_synced_commit and not is_full_sync:
                # Incremental: commits after last_synced_commit, up to end_ref
                range_spec = "%s..%s" % (last_synced_commit, end_ref)
            else:
                # Full: all commits reachable by end_ref
                range_spec = end_ref

            commits_cmd = 'git log --reverse --format="%%H" %s' % range_spec

            # Execute the git log to retrieve commit list
            try:
                output = self._run_git_command(
                    commits_cmd,
                    cwd=work_dir,
                    check_output=True
                )
                commits_to_sync = [
                    line.strip() for line in output.splitlines() if line.strip()
                ]
            except Exception as e:
                self.log_warn("Failed to get commits list: %s" % str(e))
                return False

            # If there are no commits, nothing to do
            if not commits_to_sync:
                self.log_info("No commits to sync on %s up to %s" % (source_branch, end_ref))
                return True

            self.log_info(
                "Syncing %d commits (from %s to %s)" % (
                    len(commits_to_sync), commits_to_sync[0], commits_to_sync[-1]
                )
            )

            if is_full_sync:
                try:
                    self.log_debug("Resetting to first commit: %s" % commits_to_sync[0])
                    self._run_git_command('git reset --hard %s' % commits_to_sync[0], cwd=work_dir)
                except Exception as e:
                    self.log_error("Failed to reset to first commit: %s" % str(e))
                    pass

            # Process each commit in order
            process_count = 0
            for commit_hash in commits_to_sync:
                process_count += 1
                self.log_debug("++++++++++Syncing commit: %s (%d/%d)" % (commit_hash, process_count, len(commits_to_sync)))
                success = self._sync_single_commit(
                    work_dir,
                    repo,
                    commit_hash,
                    source_branch,
                    self.config.force_full
                )
                if not success:
                    return False

            return True

        except Exception as e:
            self.log_error("Failed to sync step-by-step: %s" % str(e))
            return False
    
    def run_sync(self):
        """Run synchronization for all repositories"""
        self.log_info("Starting Git synchronization...")
        self.report['summary']['start_time'] = datetime.now().isoformat()
        self.report['summary']['total_repos'] = len(self.config.repositories)
        
        successful_repos = 0
        failed_repos = 0
        
        for repo in self.config.repositories:
            try:
                if self.sync_repository(repo):
                    successful_repos += 1
                else:
                    failed_repos += 1
            except Exception as e:
                self.log_error("Unexpected error syncing repository '%s': %s" % (repo.name, str(e)))
                failed_repos += 1
        
        self.report['summary']['successful'] = successful_repos
        self.report['summary']['failed'] = failed_repos
        self.report['summary']['end_time'] = datetime.now().isoformat()
        
        # Print summary report
        self._print_summary_report()
        
        return failed_repos == 0
    
    def _print_summary_report(self):
        """Print summary report in table format"""
        self.log_info("")
        self.log_info("-------------------- Synchronization Report --------------------")
        
        # Table header with Failed column
        header = "%-20s | %-11s | %-8s | %-8s | %-8s | %-6s | %-7s | %-5s | %s" % (
            "Repository", "Mode", "Synced", "Skipped", "New", "Failed", "Ignored", "LFS", "Status"
        )
        self.log_info(header)
        self.log_info("-" * len(header))
        
        # Table rows
        for repo_name, repo_report in self.report['repositories'].items():
            mode = repo_report.get('mode', 'unknown')
            synced = repo_report.get('branches_synced', 0)
            skipped = repo_report.get('branches_skipped', 0)
            new_branches = repo_report.get('new_branches', 0)
            failed = repo_report.get('branches_failed', 0)
            ignored_count = len(repo_report.get('ignored_branches', []))
            lfs = "true" if repo_report.get('lfs_triggered', False) else "false"
            status = repo_report.get('status', 'failed')
            
            row = "%-20s | %-11s | %-8s | %-8s | %-8s | %-6s | %-7s | %-5s | %s" % (
                repo_name[:20], mode, str(synced), str(skipped), str(new_branches), 
                str(failed), str(ignored_count), lfs, status
            )
            self.log_info(row)
        
        self.log_info("-" * len(header))
        
        # Summary statistics
        summary = self.report['summary']
        self.log_info("Total: %d repositories, Successful: %d, Failed: %d" % (
            summary['total_repos'], summary['successful'], summary['failed']
        ))


if __name__ == '__main__':
    # Argument parsing
    parser = argparse.ArgumentParser(
        description='Git Repository Synchronization Tool - Python 2.7 Implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python git_sync.py --config config.yaml
  python git_sync.py --config config.yaml --force-full -v

Features:
  - Full and incremental synchronization
  - Branch mapping and filtering
  - Git LFS support for large files
  - HTTP/SSH authentication
  - Detailed progress reporting
  - Idempotent execution
        """
    )
    parser.add_argument('--config', required=True, 
                       help='Path to YAML configuration file')
    parser.add_argument('--force-full', action='store_true', 
                       help='Force full sync for all repositories')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose/debug output')
    
    args = parser.parse_args()
    
    # Initialize tool
    tool = GitSyncTool()
    tool.config.force_full = args.force_full
    tool.config.verbose = args.verbose
    tool.verbose = args.verbose  # Set verbose attribute for _run_git_command
    
    if tool.config.verbose:
        tool.logger.setLevel(logging.DEBUG)
    
    try:
        # Check dependencies
        tool.check_dependencies()
        
        # Load configuration
        tool.load_config(args.config)
        
        tool.log_info("Git sync tool initialized successfully.")
        tool.log_info("Configuration: %d repositories, force_full=%s" % (
            len(tool.config.repositories), tool.config.force_full))
        
        # Run synchronization
        success = tool.run_sync()
        
        if success:
            tool.log_info("All repositories synchronized successfully!")
            sys.exit(0)
        else:
            tool.log_error("Some repositories failed to synchronize. Check the report above.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        tool.log_info("\nSynchronization interrupted by user.")
        sys.exit(130)
    except Exception as e:
        tool.log_error("Synchronization failed: %s" % str(e))
        if tool.config.verbose:
            import traceback
            tool.log_error("Full traceback:\n%s" % traceback.format_exc())
        sys.exit(1)
