<?php

namespace App\Http\Controllers;
use Auth;
use Hash;
use App\Models\User;
use Illuminate\Http\Request;
use Log;

class UserController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        $users = User::all();
        return response()->json($users);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validatedData = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|string|email|max:255|unique:users',
            'password' => 'required|string|min:8',
        ]);

        $user = User::create([
            'name' => $validatedData['name'],
            'email' => $validatedData['email'],
            'password' => Hash::make($validatedData['password']),
        ]);

        return response()->json($user, 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(Request $request)
{
    // Get the currently authenticated user
    $user = Auth::user();

    if (!$user) {
        return response()->json(['message' => 'User not found'], 404);
    }

    return response()->json($user);
}

    /**
     * Update the specified resource in storage.
     * */
    public function uploadImage(Request $request)
{
    // Validate the request, ensuring the image is uploaded
    $request->validate([
        'profile_image' => 'required|image|mimes:jpeg,png,jpg,gif|max:2048',
    ]);
    // Handle the uploaded image
    if ($request->hasFile('profile_image')) {
        \Log::info('Image file received');
        $image = $request->file('profile_image');
        $imagePath = $image->store('profile_images', 'public');

        // Save the image path in the database (for example, associated with a user)
        // Assuming you have a 'User' model
        $user = auth()->user(); // Assuming the user is authen  ticated
        $user->profile_image = $imagePath;
        $user->save();

        return response()->json(['message' => 'Image uploaded successfully', 'path' => $imagePath], 200);
    }

    return response()->json(['message' => 'Image upload failed'], 400);
}

public function update(Request $request)
{

    // Get the authenticated user
    $user = Auth::user();
    try {
        // Validate the request
        $request->validate([
            'name' => 'sometimes|string|max:255',
            'email' => 'sometimes|string|email|max:255|unique:users,email,' . $user->id,
            'password' => 'nullable|string|min:8',
        ]);

        // Update only the fields that are present in the request
        if ($request->has('name')) {
            $user->name = $request->input('name');
        }

        if ($request->has('email')) {
            $user->email = $request->input('email');
        }

        if ($request->filled('password')) {
            $user->password = bcrypt($request->input('password'));
        }

        $user->save();

        return response()->json(['message' => 'Profile updated successfully'], 200);
    } catch (\Exception $e) {
        return response()->json(['message' => 'An error occurred while updating the profile.'], 500);
    }
}
    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $user = User::find($id);

        if (!$user) {
            return response()->json(['message' => 'User not found'], 404);
        }

        $user->delete();

        return response()->json(['message' => 'User deleted successfully']);

    }
}
