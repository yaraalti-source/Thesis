import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:gesture_talk/screens/login_screen.dart';
import 'package:http_parser/http_parser.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  ProfilePageState createState() => ProfilePageState();
}

class ProfilePageState extends State<ProfilePage> with SingleTickerProviderStateMixin {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  bool _isEditing = false;
  bool _isUserLoading = true;
  bool _isSaving = false;
  File? _profileImage;
  String _profileImageUrl = '';
  final baseUrl = dotenv.env['BASE_URL'];
  
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _fetchUserData();
    
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeOut),
    );
    
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _fetchUserData() async {
    setState(() {
      _isUserLoading = true;
    });

    const storage = FlutterSecureStorage();
    final token = await storage.read(key: 'jwt_token');

    if (token == null) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (context) => const LoginPage()),
      );
      return;
    }

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/getUser'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _nameController.text = data['name'] ?? '';
        _emailController.text = data['email'] ?? '';
        _profileImageUrl = data['profile_image'] ?? '';
      } else {
        _showSnackBar('Failed to load profile', isError: true);
      }
    } catch (e) {
      _showSnackBar('Connection error', isError: true);
    }

    setState(() {
      _isUserLoading = false;
    });
  }

  Future<void> _logout(BuildContext context) async {
    const storage = FlutterSecureStorage();
    final token = await storage.read(key: 'jwt_token');

    if (token == null) return;

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/logout'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        await storage.delete(key: 'jwt_token');
        await storage.delete(key: 'role');
        if (mounted) {
          Navigator.of(context).pushReplacement(
            PageRouteBuilder(
              pageBuilder: (context, animation, secondaryAnimation) =>
                  const LoginPage(),
              transitionsBuilder: (context, animation, secondaryAnimation, child) {
                return FadeTransition(opacity: animation, child: child);
              },
            ),
          );
        }
      } else {
        _showSnackBar('Logout failed', isError: true);
      }
    } catch (e) {
      _showSnackBar('Connection error', isError: true);
    }
  }

  Future<void> _updateProfile() async {
    setState(() {
      _isSaving = true;
    });

    const storage = FlutterSecureStorage();
    final token = await storage.read(key: 'jwt_token');

    if (token == null) return;

    try {
      final putResponse = await http.put(
        Uri.parse('$baseUrl/api/updateUser'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'name': _nameController.text,
          'email': _emailController.text,
          if (_passwordController.text.isNotEmpty) 'password': _passwordController.text,
        }),
      );

      if (putResponse.statusCode == 200) {
        if (_profileImage != null) {
          final postRequest = http.MultipartRequest(
            'POST',
            Uri.parse('$baseUrl/api/upload-image'),
          );
          postRequest.headers['Authorization'] = 'Bearer $token';

          final imageFile = await http.MultipartFile.fromPath(
            'profile_image',
            _profileImage!.path,
            contentType: MediaType('image', 'jpeg'),
            filename: 'profile_image.jpg',
          );
          postRequest.files.add(imageFile);
          await postRequest.send();
        }

        _showSnackBar('Profile updated successfully!', isError: false);
        setState(() {
          _isEditing = false;
          _passwordController.clear();
        });
      } else {
        _showSnackBar('Failed to update profile', isError: true);
      }
    } catch (e) {
      _showSnackBar('Connection error', isError: true);
    }

    setState(() {
      _isSaving = false;
    });
  }

  void _toggleEdit() {
    setState(() {
      _isEditing = !_isEditing;
      if (!_isEditing) {
        _passwordController.clear();
      }
    });
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    try {
      final pickedFile = await picker.pickImage(source: ImageSource.gallery);
      if (pickedFile != null) {
        setState(() {
          _profileImage = File(pickedFile.path);
        });
      }
    } catch (e) {
      _showSnackBar('Error picking image', isError: true);
    }
  }

  void _showSnackBar(String message, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isError ? Icons.error_outline : Icons.check_circle_outline,
              color: isError ? AppTheme.error : AppTheme.success,
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppTheme.cardBackground,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  void _showLogoutDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.cardBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          'Logout',
          style: GoogleFonts.poppins(
            color: AppTheme.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: Text(
          'Are you sure you want to logout?',
          style: GoogleFonts.poppins(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Cancel',
              style: GoogleFonts.poppins(color: AppTheme.textMuted),
            ),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _logout(context);
            },
            child: Text(
              'Logout',
              style: GoogleFonts.poppins(color: AppTheme.error),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: SafeArea(
          child: _isUserLoading
              ? const Center(
                  child: CircularProgressIndicator(color: AppTheme.accentTeal),
                )
              : FadeTransition(
                  opacity: _fadeAnimation,
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        children: [
                          const SizedBox(height: 20),
                          
                          // Header
                          _buildHeader(),
                          
                          const SizedBox(height: 32),
                          
                          // Profile Avatar
                          _buildProfileAvatar(),
                          
                          const SizedBox(height: 32),
                          
                          // Profile Card
                          _buildProfileCard(),
                          
                          const SizedBox(height: 24),
                          
                          // Action Buttons
                          _buildActionButtons(),
                          
                          const SizedBox(height: 32),
                        ],
                      ),
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Profile',
              style: GoogleFonts.poppins(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
              ),
            ),
            Text(
              'Manage your account',
              style: GoogleFonts.poppins(
                fontSize: 14,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
        IconButton(
          onPressed: _showLogoutDialog,
          icon: const Icon(
            Icons.logout_rounded,
            color: AppTheme.textMuted,
          ),
        ),
      ],
    );
  }

  Widget _buildProfileAvatar() {
    return Stack(
      children: [
        Container(
          width: 120,
          height: 120,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: AppTheme.accentTeal.withOpacity(0.5),
              width: 3,
            ),
            boxShadow: [
              BoxShadow(
                color: AppTheme.accentTeal.withOpacity(0.3),
                blurRadius: 20,
                spreadRadius: 5,
              ),
            ],
          ),
          child: ClipOval(
            child: _profileImage != null
                ? Image.file(_profileImage!, fit: BoxFit.cover)
                : _profileImageUrl.isNotEmpty
                    ? Image.network(
                        '$baseUrl/storage/$_profileImageUrl',
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) =>
                            _buildDefaultAvatar(),
                      )
                    : _buildDefaultAvatar(),
          ),
        ),
        if (_isEditing)
          Positioned(
            bottom: 0,
            right: 0,
            child: GestureDetector(
              onTap: _pickImage,
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  gradient: AppTheme.primaryGradient,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: AppTheme.primaryDark,
                    width: 3,
                  ),
                ),
                child: const Icon(
                  Icons.camera_alt,
                  color: AppTheme.primaryDark,
                  size: 18,
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildDefaultAvatar() {
    return Container(
      color: AppTheme.cardBackground,
      child: const Icon(
        Icons.person,
        size: 60,
        color: AppTheme.textMuted,
      ),
    );
  }

  Widget _buildProfileCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: AppTheme.glassCard,
      child: Column(
        children: [
          _buildTextField(
            controller: _nameController,
            label: 'Full Name',
            icon: Icons.person_outline,
            enabled: _isEditing,
          ),
          const SizedBox(height: 20),
          _buildTextField(
            controller: _emailController,
            label: 'Email Address',
            icon: Icons.email_outlined,
            enabled: _isEditing,
            keyboardType: TextInputType.emailAddress,
          ),
          if (_isEditing) ...[
            const SizedBox(height: 20),
            _buildTextField(
              controller: _passwordController,
              label: 'New Password',
              icon: Icons.lock_outline,
              enabled: true,
              obscureText: true,
              hint: 'Leave blank to keep current',
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    bool enabled = true,
    bool obscureText = false,
    String? hint,
    TextInputType? keyboardType,
  }) {
    return TextFormField(
      controller: controller,
      enabled: enabled,
      obscureText: obscureText,
      keyboardType: keyboardType,
      style: GoogleFonts.poppins(
        color: enabled ? AppTheme.textPrimary : AppTheme.textSecondary,
        fontSize: 16,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(icon, color: AppTheme.textMuted, size: 22),
        labelStyle: GoogleFonts.poppins(color: AppTheme.textMuted),
        hintStyle: GoogleFonts.poppins(color: AppTheme.textMuted.withOpacity(0.5)),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: AppTheme.divider.withOpacity(0.2)),
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Column(
      children: [
        // Edit/Save Button
        GradientButton(
          text: _isEditing ? 'Save Changes' : 'Edit Profile',
          isLoading: _isSaving,
          onPressed: _isEditing ? _updateProfile : _toggleEdit,
          icon: _isEditing ? Icons.check : Icons.edit,
        ),
        
        if (_isEditing) ...[
          const SizedBox(height: 16),
          // Cancel Button
          GestureDetector(
            onTap: _toggleEdit,
            child: Container(
              width: double.infinity,
              height: 56,
              decoration: BoxDecoration(
                color: AppTheme.cardBackground,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppTheme.divider.withOpacity(0.3),
                ),
              ),
              child: Center(
                child: Text(
                  'Cancel',
                  style: GoogleFonts.poppins(
                    color: AppTheme.textSecondary,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
