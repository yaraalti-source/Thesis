<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use App\Models\User;
use Tests\TestCase;

class UserControllerTest extends TestCase
{
    use RefreshDatabase;

    /**
     * Test fetching the list of users.
     *
     * @return void
     */
    public function test_index_fetches_users_list()
    {
        // Create some users
        User::factory()->count(3)->create();

        // Make the request to fetch users
        $response = $this->getJson('/api/users');

        // Assert that the response is successful
        $response->assertStatus(200)
                 ->assertJsonCount(3);
    }

    /**
     * Test storing a new user.
     *
     * @return void
     */
    public function test_store_creates_new_user()
    {
        // Data for creating a new user
        $userData = [
            'name' => 'John Doe',
            'email' => 'john.doe@example.com',
            'password' => 'password123',
        ];

        // Send the request to create a new user
        $response = $this->postJson('/api/users', $userData);

        // Assert that the user was created successfully
        $response->assertStatus(201)
                 ->assertJsonFragment([
                    'name' => 'John Doe',
                    'email' => 'john.doe@example.com',
                 ]);

        // Assert that the user exists in the database
        $this->assertDatabaseHas('users', [
            'email' => 'john.doe@example.com',
        ]);
    }

    /**
     * Test showing the authenticated user.
     *
     * @return void
     */
    public function test_show_returns_authenticated_user()
    {
        // Create a user and authenticate
        $user = User::factory()->create();
        $this->actingAs($user);

        // Send request to fetch the authenticated user
        $response = $this->getJson('/api/users/me');

        // Assert that the response returns the authenticated user data
        $response->assertStatus(200)
                 ->assertJson([
                     'name' => $user->name,
                     'email' => $user->email,
                 ]);
    }


    /**
     * Test updating the user profile.
     *
     * @return void
     */
    public function test_update_user_profile()
    {
        // Create a user and authenticate
        $user = User::factory()->create();
        $this->actingAs($user);

        // Data for updating the user profile
        $updateData = [
            'name' => 'Updated Name',
            'email' => 'updated.email@example.com',
        ];

        // Send the request to update the user profile
        $response = $this->putJson('/api/users/update', $updateData);

        // Assert that the update was successful
        $response->assertStatus(200)
                 ->assertJson(['message' => 'Profile updated successfully']);

        // Assert that the user's information was updated in the database
        $this->assertDatabaseHas('users', [
            'id' => $user->id,
            'name' => 'Updated Name',
            'email' => 'updated.email@example.com',
        ]);
    }

    /**
     * Test deleting a user.
     *
     * @return void
     */
    public function test_delete_user()
    {
        // Create a user
        $user = User::factory()->create();

        // Send DELETE request to delete the user
        $response = $this->deleteJson('/api/users/' . $user->id);

        // Assert the user was deleted successfully
        $response->assertStatus(200)
                 ->assertJson(['message' => 'User deleted successfully']);

        // Assert that the user is no longer in the database
        $this->assertDatabaseMissing('users', [
            'id' => $user->id,
        ]);
    }
}
